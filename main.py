#!/usr/bin/env python3
"""
Proxy Bot Complete — Multi-source harvesting + real-time validation + MongoDB storage
Python 3.10+ required

Features:
- Harvests from multiple free proxy APIs & GitHub lists
- Validates proxies (HTTP/SOCKS) with threaded requests
- Stores only working and unique proxies in MongoDB
"""

import asyncio
import aiohttp
import re
import time
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor
from pymongo import MongoClient, ASCENDING
from pymongo.errors import DuplicateKeyError
import argparse
import requests

# ====================== CONFIG ======================
MONGO_URI = "mongodb://localhost:27017"
DB_NAME = "proxydb"
COLLECTION_NAME = "working_proxies"
VALIDATION_URL = "http://httpbin.org/ip"   # target to check proxy
VALIDATION_TIMEOUT = 8                     # seconds
TARGET_ENDPOINT = "http://16.171.170.83:3000/"  # specific endpoint to test
DEFAULT_FETCH_INTERVAL = 60               # minutes between proxy harvesting
DEFAULT_TEST_INTERVAL = 30                # minutes between endpoint testing

# Proxy sources
SOURCES = {
    "proxyscrape_http": "https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&format=text&timeout=10000",
    "proxyscrape_socks4": "https://api.proxyscrape.com/v2/?request=getproxies&protocol=socks4&format=text&timeout=10000",
    "proxyscrape_socks5": "https://api.proxyscrape.com/v2/?request=getproxies&protocol=socks5&format=text&timeout=10000",
    "the_speedx_http": "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
    "the_speedx_socks4": "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks4.txt",
    "the_speedx_socks5": "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt",
    "openproxylist_http": "https://openproxylist.xyz/http.txt",
    "proxylist_download_http": "https://www.proxy-list.download/api/v1/get?type=http",
    "geonode": "https://proxylist.geonode.com/api/proxy-list?limit=500&page=1&sort_by=lastChecked&sort_type=desc"
}

IP_PORT_REGEX = re.compile(r"(?:\d{1,3}\.){3}\d{1,3}:\d{2,5}")

# =====================================================

class ProxyBot:
    def __init__(self):
        self.client = MongoClient(MONGO_URI)
        self.db = self.client[DB_NAME]
        self.collection = self.db[COLLECTION_NAME]
        # ensure uniqueness
        self.collection.create_index(
            [("ip", ASCENDING), ("port", ASCENDING), ("protocol", ASCENDING)],
            unique=True
        )
        self.session = None

    async def fetch(self, url):
        """Fetch raw data from a URL"""
        try:
            async with self.session.get(url, timeout=20) as resp:
                if resp.status == 200:
                    if "json" in resp.content_type:
                        return await resp.json()
                    return await resp.text()
        except Exception as e:
            print(f"[!] Fetch error {url}: {e}")
        return None

    async def harvest_all(self):
        """Harvest from all sources"""
        print("[*] Harvesting proxy lists...")
        proxies = []
        async with aiohttp.ClientSession() as self.session:
            tasks = []
            for name, url in SOURCES.items():
                tasks.append(asyncio.create_task(self.harvest_source(name, url)))
            results = await asyncio.gather(*tasks)
            for r in results:
                if r:
                    proxies.extend(r)
        # remove duplicates before validation
        unique_proxies = {(p[0], p[1], p[2]) for p in proxies}
        print(f"[*] Harvested {len(unique_proxies)} unique proxies before validation")
        return list(unique_proxies)

    async def harvest_source(self, name, url):
        """Harvest from a single source"""
        raw = await self.fetch(url)
        results = []
        if not raw:
            return results

        if name == "geonode" and isinstance(raw, dict):
            for item in raw.get("data", []):
                ip = item.get("ip")
                port = int(item.get("port", 0))
                for proto in item.get("protocols", []):
                    results.append((ip, port, proto.lower()))
        elif isinstance(raw, str):
            # find ip:port
            proto_hint = "http" if "http" in name else "socks5" if "socks5" in name else "socks4"
            for ip_port in IP_PORT_REGEX.findall(raw):
                ip, port = ip_port.split(":")
                results.append((ip, int(port), proto_hint))
        return results

    def validate_proxy(self, proxy_tuple):
        """Validate if proxy works"""
        ip, port, proto = proxy_tuple
        proxy_url = f"{proto}://{ip}:{port}"
        try:
            start = time.time()
            resp = requests.get(
                VALIDATION_URL,
                proxies={proto: proxy_url, f"{proto}s": proxy_url} if proto.startswith("http") else {proto: proxy_url},
                timeout=VALIDATION_TIMEOUT
            )
            if resp.status_code == 200:
                elapsed = round(time.time() - start, 3)
                return {
                    "ip": ip, "port": port, "protocol": proto,
                    "is_working": True,
                    "response_time": elapsed,
                    "last_checked": datetime.now(timezone.utc),
                    "status_code": resp.status_code,
                    "test_url": VALIDATION_URL
                }
        except Exception:
            return None
        return None

    def store_proxy(self, proxy_doc):
        """Store in MongoDB if unique"""
        try:
            self.collection.insert_one(proxy_doc)
            print(f"[+] Working proxy added: {proxy_doc['ip']}:{proxy_doc['port']} ({proxy_doc['protocol']})")
        except DuplicateKeyError:
            # Update last_checked if already exists
            self.collection.update_one(
                {"ip": proxy_doc["ip"], "port": proxy_doc["port"], "protocol": proxy_doc["protocol"]},
                {"$set": {"last_checked": datetime.now(timezone.utc), "response_time": proxy_doc["response_time"]}}
            )

    def validate_and_store_all(self, proxies):
        """Validate all proxies with threads"""
        print("[*] Validating proxies...")
        with ThreadPoolExecutor(max_workers=120) as executor:
            for proxy_doc in executor.map(self.validate_proxy, proxies):
                if proxy_doc:
                    self.store_proxy(proxy_doc)

    def test_proxy_against_endpoint(self, proxy_doc, endpoint_url=TARGET_ENDPOINT):
        """Test a single proxy against the specific endpoint"""
        ip, port, proto = proxy_doc["ip"], proxy_doc["port"], proxy_doc["protocol"]
        proxy_url = f"{proto}://{ip}:{port}"
        
        try:
            start = time.time()
            resp = requests.get(
                endpoint_url,
                proxies={proto: proxy_url, f"{proto}s": proxy_url} if proto.startswith("http") else {proto: proxy_url},
                timeout=VALIDATION_TIMEOUT
            )
            elapsed = round(time.time() - start, 3)
            
            print(f"[+] Proxy {ip}:{port} ({proto}) -> Status: {resp.status_code}, Time: {elapsed}s")
            if resp.status_code == 200:
                try:
                    response_data = resp.json()
                    print(f"    Response: {response_data}")
                except:
                    print(f"    Response: {resp.text[:200]}...")
            
            return {
                "proxy": f"{ip}:{port}",
                "protocol": proto,
                "status_code": resp.status_code,
                "response_time": elapsed,
                "success": resp.status_code == 200,
                "endpoint": endpoint_url,
                "timestamp": datetime.now(timezone.utc)
            }
            
        except Exception as e:
            print(f"[-] Proxy {ip}:{port} ({proto}) -> Error: {str(e)}")
            return {
                "proxy": f"{ip}:{port}",
                "protocol": proto,
                "error": str(e),
                "success": False,
                "endpoint": endpoint_url,
                "timestamp": datetime.now(timezone.utc)
            }

    def test_all_proxies_against_endpoint(self, endpoint_url=TARGET_ENDPOINT):
        """Test all working proxies from database against the endpoint"""
        print(f"[*] Testing all working proxies against {endpoint_url}")
        
        # Get all working proxies from database
        working_proxies = list(self.collection.find({"is_working": True}))
        
        if not working_proxies:
            print("[!] No working proxies found in database. Run --harvest first.")
            return []
        
        print(f"[*] Found {len(working_proxies)} working proxies to test")
        
        results = []
        successful_results = []
        
        # Test each proxy
        with ThreadPoolExecutor(max_workers=50) as executor:
            future_to_proxy = {
                executor.submit(self.test_proxy_against_endpoint, proxy, endpoint_url): proxy 
                for proxy in working_proxies
            }
            
            for future in future_to_proxy:
                result = future.result()
                if result:
                    results.append(result)
                    if result.get("success"):
                        successful_results.append(result)
        
        print(f"\n[*] Testing completed!")
        print(f"[*] Total proxies tested: {len(results)}")
        print(f"[*] Successful connections: {len(successful_results)}")
        
        if successful_results:
            print(f"\n[+] Working proxies for {endpoint_url}:")
            for result in successful_results[:10]:  # Show first 10
                print(f"    {result['proxy']} ({result['protocol']}) - {result['response_time']}s")
            if len(successful_results) > 10:
                print(f"    ... and {len(successful_results) - 10} more")
        
        return results

    def run_once(self):
        """One full harvest + validation + storage cycle"""
        loop = asyncio.get_event_loop()
        harvested = loop.run_until_complete(self.harvest_all())
        self.validate_and_store_all(harvested)

    def get_proxy_stats(self):
        """Get current proxy statistics"""
        total_proxies = self.collection.count_documents({})
        working_proxies = self.collection.count_documents({"is_working": True})
        
        print(f"[*] Database Statistics:")
        print(f"    Total proxies: {total_proxies}")
        print(f"    Working proxies: {working_proxies}")
        
        return {"total": total_proxies, "working": working_proxies}

    def automated_cycle(self, fetch_interval_minutes=DEFAULT_FETCH_INTERVAL, 
                       test_interval_minutes=DEFAULT_TEST_INTERVAL, endpoint_url=TARGET_ENDPOINT):
        """Run automated fetch and test cycles"""
        print(f"[*] Starting automated proxy system")
        print(f"[*] Fetch interval: {fetch_interval_minutes} minutes")
        print(f"[*] Test interval: {test_interval_minutes} minutes")
        print(f"[*] Target endpoint: {endpoint_url}")
        print(f"[*] Started at: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
        
        last_fetch_time = 0
        last_test_time = 0
        
        # Run initial fetch
        print(f"\n[*] === INITIAL PROXY HARVEST ===")
        self.run_once()
        last_fetch_time = time.time()
        
        # Run initial test
        print(f"\n[*] === INITIAL ENDPOINT TEST ===")
        self.test_all_proxies_against_endpoint(endpoint_url)
        last_test_time = time.time()
        
        while True:
            current_time = time.time()
            
            # Check if it's time to fetch new proxies
            if (current_time - last_fetch_time) >= (fetch_interval_minutes * 60):
                print(f"\n[*] === SCHEDULED PROXY HARVEST === ({datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')})")
                self.run_once()
                last_fetch_time = current_time
                self.get_proxy_stats()
            
            # Check if it's time to test endpoint
            if (current_time - last_test_time) >= (test_interval_minutes * 60):
                print(f"\n[*] === SCHEDULED ENDPOINT TEST === ({datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')})")
                results = self.test_all_proxies_against_endpoint(endpoint_url)
                last_test_time = current_time
                
                # Log summary
                successful = len([r for r in results if r.get("success")])
                print(f"[*] Test summary: {successful}/{len(results)} proxies successful")
            
            # Sleep for 1 minute before checking again
            time.sleep(60)

    def sequential_harvest_and_test(self, interval_minutes=10, endpoint_url=TARGET_ENDPOINT):
        """Run harvest followed immediately by test, then wait for next cycle"""
        print(f"[*] Starting sequential proxy system")
        print(f"[*] Cycle interval: {interval_minutes} minutes (harvest → test → wait → repeat)")
        print(f"[*] Target endpoint: {endpoint_url}")
        print(f"[*] Started at: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"[*] Process will run continuously even when disconnected from SSH")
        
        cycle_count = 0
        
        while True:
            cycle_count += 1
            cycle_start = time.time()
            
            print(f"\n{'='*60}")
            print(f"[*] === CYCLE #{cycle_count} STARTED === ({datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')})")
            print(f"{'='*60}")
            
            # Step 1: Harvest proxies
            print(f"\n[*] 🔄 STEP 1: HARVESTING PROXIES...")
            harvest_start = time.time()
            self.run_once()
            harvest_time = round(time.time() - harvest_start, 2)
            print(f"[*] ✅ Harvest completed in {harvest_time}s")
            
            # Show current stats
            stats = self.get_proxy_stats()
            
            # Step 2: Test endpoint immediately after harvest
            print(f"\n[*] 🎯 STEP 2: TESTING ENDPOINT WITH ALL PROXIES...")
            test_start = time.time()
            results = self.test_all_proxies_against_endpoint(endpoint_url)
            test_time = round(time.time() - test_start, 2)
            
            # Summary
            successful = len([r for r in results if r.get("success")])
            total_cycle_time = round(time.time() - cycle_start, 2)
            
            print(f"\n[*] 📊 CYCLE #{cycle_count} SUMMARY:")
            print(f"    ├── Harvest time: {harvest_time}s")
            print(f"    ├── Test time: {test_time}s")
            print(f"    ├── Total proxies: {stats.get('total', 0)}")
            print(f"    ├── Working proxies: {stats.get('working', 0)}")
            print(f"    ├── Successful API calls: {successful}/{len(results)}")
            print(f"    └── Total cycle time: {total_cycle_time}s")
            
            # Wait for next cycle
            wait_time = (interval_minutes * 60) - total_cycle_time
            if wait_time > 0:
                next_cycle = datetime.now(timezone.utc) + timedelta(seconds=wait_time)
                print(f"\n[*] ⏰ Waiting {wait_time:.0f}s until next cycle...")
                print(f"[*] Next cycle at: {next_cycle.strftime('%Y-%m-%d %H:%M:%S UTC')}")
                print(f"[*] Press Ctrl+C to stop (safe to disconnect SSH)")
                time.sleep(wait_time)
            else:
                print(f"\n[*] ⚠️  Cycle took longer than interval ({total_cycle_time}s > {interval_minutes*60}s)")
                print(f"[*] Starting next cycle immediately...")

# ====================== CLI ======================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Proxy Bot Complete")
    parser.add_argument("--harvest", action="store_true", help="Run single harvest/validation cycle")
    parser.add_argument("--continuous", action="store_true", help="Run continuously (deprecated - use --auto)")
    parser.add_argument("--interval", type=int, default=30, help="Interval in minutes for continuous mode")
    parser.add_argument("--test-endpoint", action="store_true", help="Test all working proxies against the target endpoint")
    parser.add_argument("--endpoint", type=str, default=TARGET_ENDPOINT, help="Custom endpoint to test (default: http://16.171.170.83:3000/)")
    parser.add_argument("--auto", action="store_true", help="Run automated system with fetch and test cycles")
    parser.add_argument("--fetch-interval", type=int, default=DEFAULT_FETCH_INTERVAL, help="Minutes between proxy harvesting (default: 60)")
    parser.add_argument("--test-interval", type=int, default=DEFAULT_TEST_INTERVAL, help="Minutes between endpoint testing (default: 30)")
    parser.add_argument("--sequential", action="store_true", help="Run sequential mode: harvest → test → wait → repeat")
    parser.add_argument("--cycle-interval", type=int, default=10, help="Minutes between each harvest+test cycle in sequential mode (default: 10)")
    parser.add_argument("--stats", action="store_true", help="Show current proxy database statistics")
    args = parser.parse_args()

    bot = ProxyBot()

    if args.harvest:
        bot.run_once()
    elif args.continuous:
        print(f"[*] Starting continuous mode every {args.interval} min...")
        while True:
            bot.run_once()
            time.sleep(args.interval * 60)
    elif args.test_endpoint:
        bot.test_all_proxies_against_endpoint(args.endpoint)
    elif args.auto:
        try:
            bot.automated_cycle(args.fetch_interval, args.test_interval, args.endpoint)
        except KeyboardInterrupt:
            print("\n[*] Automated system stopped by user")
    elif args.sequential:
        try:
            bot.sequential_harvest_and_test(args.cycle_interval, args.endpoint)
        except KeyboardInterrupt:
            print("\n[*] Sequential system stopped by user")
    elif args.stats:
        bot.get_proxy_stats()
    else:
        parser.print_help()
