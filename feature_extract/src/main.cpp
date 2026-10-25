#include <iostream>
#include <fstream>
#include <unordered_map>
#include <string>
#include <chrono>
#include <thread>
#include <vector>
#include <algorithm>
#include <cmath>
#include <sstream> // ← needed for ostringstream in buildFlowRow()
#include <mutex>   // ← guards g_flows between capture + writer threads

#include "PcapLiveDeviceList.h"
#include "PcapLiveDevice.h"
#include "Packet.h"
#include "IPv4Layer.h"
#include "IPv6Layer.h"
#include "TcpLayer.h"
#include "UdpLayer.h"

using namespace std;
using namespace pcpp;

// .\main.exe --iface 4 --seconds 10 --label 0

using SteadyClock = std::chrono::steady_clock;

// ---------- Flow key (canonical, bidirectional) ----------
struct Endpoint
{
    string ip;
    uint16_t port;

    bool operator<(const Endpoint &other) const
    {
        if (ip != other.ip)
            return ip < other.ip;
        return port < other.port;
    }
};

struct FlowKey
{
    Endpoint a;       // canonical endpoint A
    Endpoint b;       // canonical endpoint B
    uint8_t protocol; // 6 TCP, 17 UDP

    bool operator==(const FlowKey &o) const
    {
        return a.ip == o.a.ip && a.port == o.a.port &&
               b.ip == o.b.ip && b.port == o.b.port &&
               protocol == o.protocol;
    }
};

struct FlowKeyHash
{
    size_t operator()(const FlowKey &k) const
    {
        auto h = std::hash<string>()(k.a.ip);
        h ^= (std::hash<uint16_t>()(k.a.port) << 1);
        h ^= (std::hash<string>()(k.b.ip) << 2);
        h ^= (std::hash<uint16_t>()(k.b.port) << 3);
        h ^= (std::hash<uint8_t>()(k.protocol) << 4);
        return h;
    }
};

// ---------- Flow stats ----------
struct FlowStats
{
    bool started = false;
    SteadyClock::time_point start{};
    SteadyClock::time_point last{};

    uint64_t packets = 0;
    uint64_t bytes = 0;

    uint64_t fwdPackets = 0;
    uint64_t bwdPackets = 0;
    uint64_t fwdBytes = 0;
    uint64_t bwdBytes = 0;

    // packet length stats
    uint32_t minPktLen = 0;
    uint32_t maxPktLen = 0;
    long double sumPktLen = 0.0L;
    long double sumSqPktLen = 0.0L; // for std

    // Flow inter-arrival time (IAT) stats (microseconds between packets in this flow)
    bool hasPrev = false;
    SteadyClock::time_point prev{};
    uint64_t iatCount = 0;
    long double sumIatUs = 0.0L;
    long double sumSqIatUs = 0.0L;
};

static unordered_map<FlowKey, FlowStats, FlowKeyHash> g_flows;
static std::mutex g_flowsMutex; // ← NEW: guards g_flows between capture + writer threads

static uint64_t g_raw = 0;
static uint64_t g_used = 0;
static int g_label = 0;

// ── NEW: rows loaded from previous sessions on startup ──────────────────────
static vector<string> g_prevRows;

static const string CSV_HEADER =
    "FlowID,SrcIP,DstIP,SrcPort,DstPort,Protocol,DurationMs,Packets,Bytes,"
    "FwdPackets,BwdPackets,FwdBytes,BwdBytes,"
    "MinPktLen,MaxPktLen,MeanPktLen,StdPktLen,"
    "FlowIATMeanUs,FlowIATStdUs,"
    "PacketsPerSec,BytesPerSec,FwdPps,BwdPps,Label";

// ── NEW: load any existing flows.csv rows into g_prevRows ───────────────────
static void loadExistingFlows()
{
    ifstream f("flows.csv");
    if (!f.good())
        return;

    string header;
    getline(f, header); // skip header line

    string line;
    while (getline(f, line))
    {
        if (!line.empty())
            g_prevRows.push_back(line);
    }

    cout << "Loaded " << g_prevRows.size() << " existing flow rows from flows.csv\n";
}

static bool isForward(const FlowKey &key, const Endpoint &src)
{
    return (src.ip == key.a.ip && src.port == key.a.port);
}

static bool parseArgs(int argc, char *argv[], int &ifaceIndex, int &seconds, int &label)
{
    ifaceIndex = 0;
    seconds = 20;
    label = 0;

    for (int i = 1; i < argc; i++)
    {
        string arg = argv[i];
        if (arg == "--iface" && i + 1 < argc)
        {
            ifaceIndex = stoi(argv[++i]);
        }
        else if (arg == "--seconds" && i + 1 < argc)
        {
            seconds = stoi(argv[++i]);
        }
        else if (arg == "--label" && i + 1 < argc)
        {
            label = stoi(argv[++i]);
        }
        else if (arg == "--help")
        {
            cout << "Usage: main.exe [--iface N] [--seconds N] [--label 0/1]\n";
            return false;
        }
    }
    return true;
}

static inline long double ld_sqrt(long double x)
{
    return (x <= 0.0L) ? 0.0L : sqrt((double)x);
}

// ── NEW: build one CSV row string for a flow ────────────────────────────────
static string buildFlowRow(const FlowKey &k, const FlowStats &s, int label)
{
    auto durMs = std::chrono::duration_cast<std::chrono::milliseconds>(s.last - s.start).count();
    long double durSec = (durMs <= 0) ? 0.000001L : (durMs / 1000.0L);

    long double pps = (long double)s.packets / durSec;
    long double bps = (long double)s.bytes / durSec;
    long double fwdPps = (long double)s.fwdPackets / durSec;
    long double bwdPps = (long double)s.bwdPackets / durSec;

    long double meanLen = (s.packets > 0) ? (s.sumPktLen / (long double)s.packets) : 0.0L;
    long double varLen = 0.0L;
    if (s.packets > 1)
    {
        long double ex2 = s.sumSqPktLen / (long double)s.packets;
        varLen = ex2 - (meanLen * meanLen);
        if (varLen < 0)
            varLen = 0;
    }
    long double stdLen = ld_sqrt(varLen);

    long double iatMean = (s.iatCount > 0) ? (s.sumIatUs / (long double)s.iatCount) : 0.0L;
    long double iatVar = 0.0L;
    if (s.iatCount > 1)
    {
        long double ex2 = s.sumSqIatUs / (long double)s.iatCount;
        iatVar = ex2 - (iatMean * iatMean);
        if (iatVar < 0)
            iatVar = 0;
    }
    long double iatStd = ld_sqrt(iatVar);

    string flowId = k.a.ip + ":" + to_string(k.a.port) + "-" +
                    k.b.ip + ":" + to_string(k.b.port) + "-P" + to_string((int)k.protocol);

    // Build the row into a string stream so we can return it as a string
    ostringstream row;
    row << fixed;
    row.precision(6);

    row << flowId << ","
        << k.a.ip << ","
        << k.b.ip << ","
        << k.a.port << ","
        << k.b.port << ","
        << (int)k.protocol << ","
        << durMs << ","
        << s.packets << ","
        << s.bytes << ","
        << s.fwdPackets << ","
        << s.bwdPackets << ","
        << s.fwdBytes << ","
        << s.bwdBytes << ","
        << s.minPktLen << ","
        << s.maxPktLen << ","
        << (double)meanLen << ","
        << (double)stdLen << ","
        << (double)iatMean << ","
        << (double)iatStd << ","
        << (double)pps << ","
        << (double)bps << ","
        << (double)fwdPps << ","
        << (double)bwdPps << ","
        << label;

    return row.str();
}

// ── NEW: rewrite flows.csv = header + previous session rows + current flows ─
static void flushFlowsCSV()
{
    ofstream csv("flows.csv"); // full overwrite each flush
    csv << CSV_HEADER << "\n";

    // Previous sessions' rows (unchanged)
    for (const auto &row : g_prevRows)
        csv << row << "\n";

    // Current session's live flows (latest stats)
    {
        std::lock_guard<std::mutex> lock(g_flowsMutex);
        for (const auto &kv : g_flows)
            csv << buildFlowRow(kv.first, kv.second, g_label) << "\n";
    }
}

// ─────────────────────────────────────────────────────────────────────────────

void onPacketArrives(RawPacket *rawPacket, PcapLiveDevice *, void *)
{
    g_raw++;

    Packet packet(rawPacket);

    // IP layer (IPv4 or IPv6)
    string srcIP, dstIP;
    uint8_t proto = 0;

    auto ip4 = packet.getLayerOfType<IPv4Layer>();
    auto ip6 = packet.getLayerOfType<IPv6Layer>();
    if (!ip4 && !ip6)
        return;

    if (ip4)
    {
        srcIP = ip4->getSrcIPAddress().toString();
        dstIP = ip4->getDstIPAddress().toString();
        proto = ip4->getIPv4Header()->protocol;
    }
    else
    {
        srcIP = ip6->getSrcIPAddress().toString();
        dstIP = ip6->getDstIPAddress().toString();
        proto = ip6->getIPv6Header()->nextHeader;
    }

    // Only TCP/UDP
    uint16_t srcPort = 0, dstPort = 0;
    if (packet.isPacketOfType(TCP))
    {
        auto tcp = packet.getLayerOfType<TcpLayer>();
        if (!tcp)
            return;
        srcPort = tcp->getSrcPort();
        dstPort = tcp->getDstPort();
        proto = 6;
    }
    else if (packet.isPacketOfType(UDP))
    {
        auto udp = packet.getLayerOfType<UdpLayer>();
        if (!udp)
            return;
        srcPort = udp->getSrcPort();
        dstPort = udp->getDstPort();
        proto = 17;
    }
    else
    {
        return;
    }

    Endpoint src{srcIP, srcPort};
    Endpoint dst{dstIP, dstPort};

    // Canonicalize key so reverse direction updates same flow
    FlowKey key;
    key.protocol = proto;
    if (dst < src)
    {
        key.a = dst;
        key.b = src;
    }
    else
    {
        key.a = src;
        key.b = dst;
    }

    auto now = SteadyClock::now();
    uint32_t len = rawPacket->getRawDataLen();

    {
        std::lock_guard<std::mutex> lock(g_flowsMutex); // ← guard map writes
        auto &st = g_flows[key];

        if (!st.started)
        {
            st.started = true;
            st.start = now;
            st.last = now;

            st.minPktLen = len;
            st.maxPktLen = len;
            st.sumPktLen = len;
            st.sumSqPktLen = (long double)len * (long double)len;

            st.prev = now;
            st.hasPrev = true;
        }
        else
        {
            st.last = now;

            // IAT update
            if (st.hasPrev)
            {
                auto iatUs = std::chrono::duration_cast<std::chrono::microseconds>(now - st.prev).count();
                if (iatUs < 0)
                    iatUs = 0;
                st.iatCount++;
                st.sumIatUs += (long double)iatUs;
                st.sumSqIatUs += (long double)iatUs * (long double)iatUs;
            }
            st.prev = now;

            // Packet length updates
            if (len < st.minPktLen)
                st.minPktLen = len;
            if (len > st.maxPktLen)
                st.maxPktLen = len;
            st.sumPktLen += len;
            st.sumSqPktLen += (long double)len * (long double)len;
        }

        st.packets += 1;
        st.bytes += len;

        if (isForward(key, src))
        {
            st.fwdPackets++;
            st.fwdBytes += len;
        }
        else
        {
            st.bwdPackets++;
            st.bwdBytes += len;
        }
    } // ← mutex released here

    g_used++;

    // live counters
    cout << "\rRaw: " << g_raw
         << " | Used(TCP/UDP): " << g_used
         << " | Flows: " << g_flows.size()
         << "     " << flush;
}

static bool g_capturing = true;

void statsWriter(int totalSeconds)
{
    int sessionNum = 1;
    uint64_t totalFlows = 0;

    ifstream sf("stats.csv");
    if (sf.good())
    {
        string line1, line2;
        getline(sf, line1);
        if (getline(sf, line2))
        {
            int last_comma = line2.rfind(',');
            if (last_comma != string::npos)
                sessionNum = stoi(line2.substr(last_comma + 1)) + 1;

            string temp = line2.substr(0, last_comma);
            int prev_comma = temp.rfind(',');
            if (prev_comma != string::npos)
                totalFlows = stoull(temp.substr(prev_comma + 1));
        }
    }
    sf.close();

    cout << "statsWriter started\n";
    long long elapsed = 0;
    auto start = SteadyClock::now();

    while (g_capturing)
    {
        elapsed = std::chrono::duration_cast<std::chrono::seconds>(
                      SteadyClock::now() - start)
                      .count();

        // ── stats.csv (unchanged) ──────────────────────────────────────────
        {
            ofstream stats("stats.csv");
            stats << "raw,used,flows,elapsed,total,total_flows,session\n";
            stats << g_raw << "," << g_used << "," << g_flows.size() << ","
                  << elapsed << "," << totalSeconds << ","
                  << totalFlows + g_flows.size() << "," << sessionNum << "\n";
        }

        // ── NEW: live flush of flows.csv every second ──────────────────────
        flushFlowsCSV();

        std::this_thread::sleep_for(std::chrono::seconds(1));
    }

    // Final flush after capture stops
    {
        ofstream statsFinal("stats.csv");
        statsFinal << "raw,used,flows,elapsed,total,total_flows,session\n";
        statsFinal << g_raw << "," << g_used << "," << g_flows.size() << ","
                   << totalSeconds << "," << totalSeconds << ","
                   << totalFlows + g_flows.size() << "," << sessionNum << "\n";
    }

    flushFlowsCSV(); // ← final authoritative write
    cout << "statsWriter stopped\n";
}

int main(int argc, char *argv[])
{
    for (int i = 1; i < argc; i++)
    {
        if (string(argv[i]) == "--list")
        {
            auto &devList = PcapLiveDeviceList::getInstance();
            auto devices = devList.getPcapLiveDevicesList();
            for (size_t i = 0; i < devices.size(); i++)
                cout << i << ": " << devices[i]->getName()
                     << " | " << devices[i]->getDesc() << "\n";
            return 0;
        }
    }

    int ifaceIndex = 0;
    int seconds = 20;
    int label = 0;

    if (!parseArgs(argc, argv, ifaceIndex, seconds, label))
        return 0;

    g_label = label;

    // ── NEW: load previous session rows before anything else ────────────────
    loadExistingFlows();

    auto &devList = PcapLiveDeviceList::getInstance();
    auto devices = devList.getPcapLiveDevicesList();

    if (devices.empty())
    {
        cerr << "No capture devices found.\n";
        cerr << "Check that Npcap is installed.\n";
        return 1;
    }

    cout << "Available devices:\n";
    for (size_t i = 0; i < devices.size(); i++)
        cout << i << ": " << devices[i]->getName()
             << " | " << devices[i]->getDesc() << "\n";

    if (ifaceIndex < 0 || ifaceIndex >= (int)devices.size())
    {
        cerr << "\nInvalid --iface index. Pick from the list above.\n";
        return 1;
    }

    PcapLiveDevice *dev = devices[ifaceIndex];

    cout << "\nUsing device index: " << ifaceIndex << "\n";
    cout << "Device desc: " << dev->getDesc() << "\n";
    cout << "Capturing for " << seconds << " seconds...\n";
    cout << "Label for this run: " << label << "\n";
    cout << "Tip: open a website or run 'ping google.com' during capture.\n";
    cout << "Tip: run this terminal as Administrator.\n\n";

    if (!dev->open())
    {
        cerr << "Cannot open device.\n";
        cerr << "Try running the terminal as Administrator.\n";
        return 1;
    }

    g_capturing = true;
    std::thread statsThread(statsWriter, seconds);

    dev->startCapture(onPacketArrives, nullptr);
    std::this_thread::sleep_for(std::chrono::seconds(seconds));
    dev->stopCapture();
    dev->close();

    g_capturing = false;
    statsThread.join();

    cout << "\n\nCapture finished.\n";
    cout << "Raw packets seen   : " << g_raw << "\n";
    cout << "Used TCP/UDP pkts  : " << g_used << "\n";
    cout << "Flows this session : " << g_flows.size() << "\n";
    cout << "Total rows in CSV  : " << g_prevRows.size() + g_flows.size() << "\n";
    cout << "CSV written        : flows.csv\n";

    if (g_used == 0)
    {
        cout << "\nNo TCP/UDP packets were captured.\n";
        cout << "Fixes:\n";
        cout << " - Run as Administrator\n";
        cout << " - Choose the correct Wi-Fi/Ethernet device index\n";
        cout << " - Generate traffic while capturing\n";
    }

    return 0;
}
