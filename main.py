import asyncio
import aiohttp
import json
import re
import random
import time
import sys


USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:135.0) Gecko/20100101 Firefox/135.0'
]


async def send_one(session, action, data, referer):
    try:
        await asyncio.sleep(random.uniform(0.08, 0.35))
        headers = {
            'User-Agent': random.choice(USER_AGENTS),
            'Referer': referer
        }
        async with session.post(action, data=data, headers=headers, timeout=25) as resp:
            return resp.status in (200, 302)
    except Exception:
        return False


async def raid_the_form(url, num_submissions, concurrency):
    connector = aiohttp.TCPConnector(limit_per_host=concurrency, ssl=False)
    timeout = aiohttp.ClientTimeout(total=35)
    
    async with aiohttp.ClientSession(connector=connector, timeout=timeout, cookie_jar=aiohttp.CookieJar()) as session:
        headers = {'User-Agent': random.choice(USER_AGENTS)}
        async with session.get(url, headers=headers) as resp:
            if resp.status != 200:
                raise ValueError(f"Failed to load form: {resp.status}")
            html = await resp.text()
        
        data_str = None
        match = re.search(r'FB_PUBLIC_LOAD_DATA_ = (.*?);', html, re.DOTALL)
        if match:
            data_str = match.group(1)
        else:
            match = re.search(r'_docs_flag_initialData = (.*?);', html, re.DOTALL)
            if match:
                data_str = match.group(1)
        
        if not data_str:
            raise ValueError("Could not find form data on the page")
        
        data = json.loads(data_str)
        if len(data) < 2 or not isinstance(data[1], list) or len(data[1]) < 2:
            raise ValueError("Weird Google Forms data structure")
        
        questions = data[1][1]
        
        action_match = re.search(r'<form[^>]*action=["\']([^"\']+)["\']', html, re.IGNORECASE)
        if not action_match:
            raise ValueError("Form action not found")
        action = action_match.group(1)
        if not action.startswith('http'):
            base = re.match(r'(https?://[^/]+)', url)
            action = base.group(1) + action if base else action
        
        tasks = [send_one(session, action, make_random_answers(questions), url) for _ in range(num_submissions)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
    ok = sum(1 for r in results if r is True)
    print(f"\nSuccessfully submitted: {ok}/{num_submissions} forms")


def make_random_answers(questions):
    answers = {}
    for q in questions:
        if len(q) < 5 or not q[4]:
            continue
        field_info = q[4][0]
        field_id = field_info[0]
        options = field_info[1]
        is_required = field_info[2] if len(field_info) > 2 else False
        q_type = q[3]
        key = f'entry.{field_id}'
        
        if q_type == 2:
            if options:
                good_opts = [opt for opt in options if not (len(opt) > 4 and opt[4])]
                if not good_opts:
                    good_opts = options
                if good_opts and (is_required or random.random() > 0.4):
                    answers[key] = random.choice(good_opts)[0]
        elif q_type == 4:
            if options:
                good_opts = [opt for opt in options if not (len(opt) > 4 and opt[4])]
                if not good_opts:
                    good_opts = options
                if good_opts and (is_required or random.random() > 0.4):
                    how_many = random.randint(1 if is_required else 0, len(good_opts))
                    picked = random.sample(good_opts, how_many)
                    answers[key] = [x[0] for x in picked]
        elif q_type in (0, 1, 3):
            if is_required or random.random() > 0.35:
                answers[key] = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=random.randint(9, 32)))
        elif q_type == 7:
            if options:
                good_opts = [opt for opt in options if opt]
                if good_opts and (is_required or random.random() > 0.4):
                    choice = random.choice(good_opts)
                    answers[key] = choice[0] if isinstance(choice, list) else choice
    return answers


if __name__ == "__main__":
    url = None
    num_submissions = 1000
    concurrency = 25
    
    if len(sys.argv) > 1 and not sys.argv[1].startswith('-'):
        url = sys.argv[1]
    if len(sys.argv) > 2:
        try:
            num_submissions = int(sys.argv[2])
        except:
            pass
    if len(sys.argv) > 3:
        try:
            concurrency = int(sys.argv[3])
        except:
            pass
    
    if not url:
        url = input("Enter Google Form URL: ").strip()
    
    if not url.startswith("http"):
        print("Error: Please provide a valid URL")
        sys.exit(1)
    
    print("Launching raid...")
    start = time.time()
    try:
        asyncio.run(raid_the_form(url, num_submissions, concurrency))
    except Exception as e:
        print(f"Error: {e}")
    print(f"Total time: {time.time() - start:.1f} seconds")
