import aiohttp
import asyncio
import json
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader
from datetime import datetime
import pytz

# Headers to mimic a real browser request
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:136.0) Gecko/20100101 Firefox/136.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}


async def fetch_results(session, num):
    url = f"https://results.eci.gov.in/ResultAcGenFeb2025/ConstituencywiseU05{num}.htm"

    try:
        async with session.get(url, headers=HEADERS, timeout=10) as response:
            if response.status != 200:
                print(f"Failed to fetch {url} (HTTP {response.status})")
                return None, None

            html = await response.text()
            soup = BeautifulSoup(html, "html.parser")

            # Extract constituency name
            constituency_elem = soup.find("h2")
            if constituency_elem:
                constituency_name = (
                    constituency_elem.find("span")
                    .get_text(strip=True)
                    .replace("(NCT of Delhi)", "")
                )
            else:
                print(f"Could not extract constituency name from {url}")
                return None, None

            # Find the table with election results
            table = soup.find("table", class_="table-striped")
            if not table:
                print(f"Could not find results table in {url}")
                return constituency_name, None

            results = []
            rows = table.find("tbody").find_all("tr")

            for row in rows:
                columns = row.find_all("td")
                if len(columns) >= 7:
                    candidate_name = columns[1].get_text(strip=True)
                    party = columns[2].get_text(strip=True)
                    evm_votes = columns[3].get_text(strip=True)
                    postal_votes = columns[4].get_text(strip=True)
                    total_votes = columns[5].get_text(strip=True)
                    vote_percentage = columns[6].get_text(strip=True)

                    results.append(
                        {
                            "Constituency": constituency_name,
                            "Constituency URL": url,
                            "Candidate": candidate_name,
                            "Party": party,
                            "EVM Votes": evm_votes,
                            "Postal Votes": postal_votes,
                            "Total Votes": total_votes,
                            "Vote %": vote_percentage,
                        }
                    )

            return constituency_name, results

    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None, None


async def get_all_results():
    all_results = {}

    async with aiohttp.ClientSession() as session:
        tasks = [fetch_results(session, i) for i in range(1, 71)]
        responses = await asyncio.gather(*tasks)

    for constituency, results in responses:
        if results:
            all_results[constituency] = results

    return all_results


async def main():
    results = await get_all_results()

    # Save results to JSON
    with open("candidates_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, ensure_ascii=False)

    print("Results saved to candidates_results.json")


# Load Jinja2 environment and templates from the "templates" directory


def generate_independent_html(data, output_file="independent_candidates.html"):
    """Generates an HTML file listing only independent candidates across all constituencies."""
    env = Environment(loader=FileSystemLoader("templates"))
    ist = pytz.timezone("Asia/Kolkata")
    last_updated = datetime.now(ist).strftime("%Y-%m-%d %H:%M:%S")
    template = env.get_template("independent_template.html")
    html_content = template.render(candidates=data, last_updated=last_updated)
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"✅ Independent candidates HTML generated: {output_file}")


def generate_all_results_html(data, output_file="all_candidates.html"):
    """Generates an HTML file listing all candidates by constituency."""
    env = Environment(loader=FileSystemLoader("templates"))
    ist = pytz.timezone("Asia/Kolkata")
    last_updated = datetime.now(ist).strftime("%Y-%m-%d %H:%M:%S")
    template = env.get_template("all_candidates_template.html")
    html_content = template.render(results=data, last_updated=last_updated)
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"✅ All candidates HTML generated: {output_file}")


if __name__ == "__main__":
    asyncio.run(main())
    with open("candidates_results.json") as f:
        data = json.load(f)

    generate_independent_html(data)
    generate_all_results_html(data)
