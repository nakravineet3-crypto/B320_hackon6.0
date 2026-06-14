import httpx
import asyncio
import time

BASE = "http://localhost:8000"


async def run_tests():
    async with httpx.AsyncClient(timeout=30) as client:
        results = []

        # Test 1: Health
        r = await client.get(f"{BASE}/health")
        results.append(("Health", r.status_code == 200))

        # Test 2: Parse
        r = await client.post(
            f"{BASE}/api/mission/parse",
            json={"goal": "Birthday party for 12 kids tomorrow under 4000"},
        )
        d = r.json()["data"]
        results.append(("Parse - domain", d.get("domain") == "event"))
        results.append(("Parse - headcount", d.get("headcount") == 12))
        results.append(("Parse - safety", d.get("safety_context") == "child_safe"))

        # Test 3: Build speed
        start = time.time()
        r = await client.post(
            f"{BASE}/api/mission/build",
            json={"goal": "Birthday party for 12 kids tomorrow under 4000"},
        )
        elapsed = time.time() - start
        d = r.json()["data"]
        results.append(("Build - success", r.status_code == 200))
        results.append(("Build - items", len(d.get("cart_items", [])) >= 6))
        results.append((
            "Build - no sponsored",
            not any(i.get("is_sponsored") for i in d.get("cart_items", [])),
        ))
        results.append((
            "Build - community fields",
            all("community_adoption_score" in i for i in d.get("cart_items", [])),
        ))
        results.append(("Build - under 3s", elapsed < 3.0))

        # Test 4: Audit
        r = await client.post(
            f"{BASE}/api/mission/audit",
            json={"cart_items": [], "headcount": 12, "occasion": "birthday"},
        )
        d = r.json()["data"]
        flags = d.get("flags", [])
        results.append(("Audit - 4 flags", len(flags) == 4))
        results.append((
            "Audit - flag4 blue",
            flags[3].get("severity") == "blue" if len(flags) == 4 else False,
        ))
        results.append((
            "Audit - repaired total",
            d.get("repaired_total") == 3850,
        ))

        # Test 5: Demo endpoints
        r = await client.get(f"{BASE}/api/demo/occasions")
        results.append(("Occasions", len(r.json()["data"]) == 4))

        r = await client.get(f"{BASE}/api/demo/reorder-alerts")
        results.append(("Reorder alerts", len(r.json()["data"]) == 3))

        # Test 6: Home setup domain
        r = await client.post(
            f"{BASE}/api/mission/build",
            json={"goal": "New flat setup this weekend under 15000"},
        )
        d = r.json()["data"]
        cats = [i.get("category", "") for i in d.get("cart_items", [])]
        party = ["plates", "cups", "balloons", "candles"]
        results.append((
            "Home setup - no party items",
            not any(c in party for c in cats),
        ))

        # Print results
        print("\n" + "=" * 50)
        print("MISSIONCART DEMO READINESS TEST")
        print("=" * 50)
        passed = 0
        failed = 0
        for name, result in results:
            status = "PASS" if result else "FAIL"
            icon = "[v]" if result else "[x]"
            print(f"  {icon} {name}: {status}")
            if result:
                passed += 1
            else:
                failed += 1
        print("=" * 50)
        print(f"  {passed}/{passed+failed} tests passing")
        confidence = (passed / (passed + failed)) * 100
        print(f"  Demo confidence: {confidence:.0f}%")
        if failed == 0:
            print("  STATUS: DEMO READY")
        elif failed <= 2:
            print("  STATUS: MOSTLY READY - fix failing tests")
        else:
            print("  STATUS: NOT READY - critical fixes needed")
        print("=" * 50)


asyncio.run(run_tests())
