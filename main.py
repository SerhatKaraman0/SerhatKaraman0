import os
import requests
from datetime import datetime
import time
import hashlib
import xml.etree.ElementTree as etree
import formatter
from dotenv import load_dotenv

load_dotenv()
# Ensure SVGs are written with standard namespaces (no ns0 prefix)
etree.register_namespace('', 'http://www.w3.org/2000/svg')
etree.register_namespace('xlink', 'http://www.w3.org/1999/xlink')

HEADERS = {'authorization': 'token '+ os.environ['ACCESS_TOKEN']}
USER_NAME = os.environ['USER_NAME']
OWNER_ID = None  
QUERY_COUNT = {'user_getter': 0, 'follower_getter': 0, 'graph_repos_stars': 0, 'recursive_loc': 0, 'graph_commits': 0, 'loc_query': 0}

def request_maker(func_name, query, variables):
    """
    Returns a request, or raises an Exception if the response does not succeed.
    """
    request = requests.post('https://api.github.com/graphql', json={'query': query, 'variables':variables}, headers=HEADERS)
    if request.status_code == 200:
        return request
    raise Exception(func_name, ' has failed with a', request.status_code, request.text, QUERY_COUNT)

def perf_counter(funct, *args):
    """
    Calculates the time it takes for a function to run
    Returns the function result and the time differential
    """
    start = time.perf_counter()
    funct_return = funct(*args)
    return funct_return, time.perf_counter() - start


def graph_commits(start_date, end_date):
    """
    Uses GitHub's GraphQL v4 API to return my total commit count
    """
    query_count('graph_commits')
    query = '''
    query($start_date: DateTime!, $end_date: DateTime!, $login: String!) {
        user(login: $login) {
            contributionsCollection(from: $start_date, to: $end_date) {
                contributionCalendar {
                    totalContributions
                }
            }
        }
    }'''
    variables = {'start_date': start_date,'end_date': end_date, 'login': USER_NAME}
    request = request_maker(graph_commits.__name__, query, variables)
    return int(request.json()['data']['user']['contributionsCollection']['contributionCalendar']['totalContributions'])

def user_getter(username):
    """
    Returns the account ID and creation time of the user
    """
    query_count('user_getter')
    query = '''
    query($login: String!){
        user(login: $login) {
            id
            createdAt
        }
    }'''
    variables = {'login': username}
    request = request_maker(user_getter.__name__, query, variables)
    return {'id': request.json()['data']['user']['id']}, request.json()['data']['user']['createdAt']

def commit_counter(comment_size):
    """
    Counts up my total commits, using the cache file created by cache_builder.
    """
    total_commits = 0
    filename = 'cache/'+hashlib.sha256(USER_NAME.encode('utf-8')).hexdigest()+'.txt' # Use the same filename as cache_builder
    with open(filename, 'r') as f:
        data = f.readlines()
    cache_comment = data[:comment_size] # save the comment block
    data = data[comment_size:] # remove those lines
    for line in data:
        total_commits += int(line.split()[2])
    return total_commits

def cache_builder(edges, comment_size, force_cache, loc_add=0, loc_del=0):
    """
    Checks each repository in edges to see if it has been updated since the last time it was cached
    If it has, run recursive_loc on that repository to update the LOC count
    """
    cached = True # Assume all repositories are cached
    filename = 'cache/'+hashlib.sha256(USER_NAME.encode('utf-8')).hexdigest()+'.txt' # Create a unique filename for each user
    try:
        with open(filename, 'r') as f:
            data = f.readlines()
    except FileNotFoundError: # If the cache file doesn't exist, create it
        data = []
        if comment_size > 0:
            for _ in range(comment_size): data.append('This line is a comment block. Write whatever you want here.\n')
        with open(filename, 'w') as f:
            f.writelines(data)

    if len(data)-comment_size != len(edges) or force_cache: # If the number of repos has changed, or force_cache is True
        cached = False
        flush_cache(edges, filename, comment_size)
        with open(filename, 'r') as f:
            data = f.readlines()

    cache_comment = data[:comment_size] # save the comment block
    data = data[comment_size:] # remove those lines
    for index in range(len(edges)):
        repo_hash, commit_count, *__ = data[index].split()
        if repo_hash == hashlib.sha256(edges[index]['node']['nameWithOwner'].encode('utf-8')).hexdigest():
            try:
                if int(commit_count) != edges[index]['node']['defaultBranchRef']['target']['history']['totalCount']:
                    # if commit count has changed, update loc for that repo
                    owner, repo_name = edges[index]['node']['nameWithOwner'].split('/')
                    loc = recursive_loc(owner, repo_name, data, cache_comment)
                    data[index] = repo_hash + ' ' + str(edges[index]['node']['defaultBranchRef']['target']['history']['totalCount']) + ' ' + str(loc[2]) + ' ' + str(loc[0]) + ' ' + str(loc[1]) + '\n'
            except TypeError: # If the repo is empty
                data[index] = repo_hash + ' 0 0 0 0\n'
    with open(filename, 'w') as f:
        f.writelines(cache_comment)
        f.writelines(data)
    for line in data:
        loc = line.split()
        loc_add += int(loc[3])
        loc_del += int(loc[4])
    return [loc_add, loc_del, loc_add - loc_del, cached]

def flush_cache(edges, filename, comment_size):
    """
    Wipes the cache file
    This is called when the number of repositories changes or when the file is first created
    """
    with open(filename, 'r') as f:
        data = []
        if comment_size > 0:
            data = f.readlines()[:comment_size] # only save the comment
    with open(filename, 'w') as f:
        f.writelines(data)
        for node in edges:
            f.write(hashlib.sha256(node['node']['nameWithOwner'].encode('utf-8')).hexdigest() + ' 0 0 0 0\n')

def query_count(funct_id):
    """
    Counts how many times the GitHub GraphQL API is called
    """
    global QUERY_COUNT
    QUERY_COUNT[funct_id] += 1

def stars_counter(data):
    """
    Count total stars in repositories owned by me
    """
    total_stars = 0
    for node in data: total_stars += node['node']['stargazers']['totalCount']
    return total_stars

def add_archive():
    """
    Several repositories I have contributed to have since been deleted.
    This function adds them using their last known data
    """
    with open('cache/repository_archive.txt', 'r') as f:
        data = f.readlines()
    old_data = data
    data = data[7:len(data)-3] # remove the comment block    
    added_loc, deleted_loc, added_commits = 0, 0, 0
    contributed_repos = len(data)
    for line in data:
        repo_hash, total_commits, my_commits, *loc = line.split()
        added_loc += int(loc[0])
        deleted_loc += int(loc[1])
        if (my_commits.isdigit()): added_commits += int(my_commits)
    added_commits += int(old_data[-1].split()[4][:-1])
    return [added_loc, deleted_loc, added_loc - deleted_loc, added_commits, contributed_repos]

def follower_getter(username):
    """
    Returns the number of followers of the user
    """
    query_count('follower_getter')
    query = '''
    query($login: String!){
        user(login: $login) {
            followers {
                totalCount
            }
        }
    }'''
    request = request_maker(follower_getter.__name__, query, {'login': username})
    return int(request.json()['data']['user']['followers']['totalCount'])

def graph_repos_stars(count_type, owner_affiliation, cursor=None, add_loc=0, del_loc=0):
    """
    Uses GitHub's GraphQL v4 API to return my total repository, star, or lines of code count.
    """
    query_count('graph_repos_stars')
    query = '''
    query ($owner_affiliation: [RepositoryAffiliation], $login: String!, $cursor: String) {
        user(login: $login) {
            repositories(first: 100, after: $cursor, ownerAffiliations: $owner_affiliation) {
                totalCount
                edges {
                    node {
                        ... on Repository {
                            nameWithOwner
                            stargazers {
                                totalCount
                            }
                        }
                    }
                }
                pageInfo {
                    endCursor
                    hasNextPage
                }
            }
        }
    }'''
    variables = {'owner_affiliation': owner_affiliation, 'login': USER_NAME, 'cursor': cursor}
    request = request_maker(graph_repos_stars.__name__, query, variables)
    if request.status_code == 200:
        if count_type == 'repos':
            return request.json()['data']['user']['repositories']['totalCount']
        elif count_type == 'stars':
            return stars_counter(request.json()['data']['user']['repositories']['edges'])

def force_close_file(data, cache_comment):
    """
    Forces the file to close, preserving whatever data was written to it
    This is needed because if this function is called, the program would've crashed before the file is properly saved and closed
    """
    filename = 'cache/'+hashlib.sha256(USER_NAME.encode('utf-8')).hexdigest()+'.txt'
    with open(filename, 'w') as f:
        f.writelines(cache_comment)
        f.writelines(data)
    print('There was an error while writing to the cache file. The file,', filename, 'has had the partial data saved and closed.')


def recursive_loc(owner, repo_name, data, cache_comment, addition_total=0, deletion_total=0, my_commits=0, cursor=None):
    """
    Uses GitHub's GraphQL v4 API and cursor pagination to fetch 100 commits from a repository at a time
    """
    query_count('recursive_loc')
    query = '''
    query ($repo_name: String!, $owner: String!, $cursor: String) {
        repository(name: $repo_name, owner: $owner) {
            defaultBranchRef {
                target {
                    ... on Commit {
                        history(first: 100, after: $cursor) {
                            totalCount
                            edges {
                                node {
                                    ... on Commit {
                                        committedDate
                                    }
                                    author {
                                        user {
                                            id
                                        }
                                    }
                                    deletions
                                    additions
                                }
                            }
                            pageInfo {
                                endCursor
                                hasNextPage
                            }
                        }
                    }
                }
            }
        }
    }'''
    variables = {'repo_name': repo_name, 'owner': owner, 'cursor': cursor}
    request = requests.post('https://api.github.com/graphql', json={'query': query, 'variables':variables}, headers=HEADERS) # I cannot use simple_request(), because I want to save the file before raising Exception
    if request.status_code == 200:
        if request.json()['data']['repository']['defaultBranchRef'] != None: # Only count commits if repo isn't empty
            return loc_counter_one_repo(owner, repo_name, data, cache_comment, request.json()['data']['repository']['defaultBranchRef']['target']['history'], addition_total, deletion_total, my_commits)
        else: return 0
    force_close_file(data, cache_comment) # saves what is currently in the file before this program crashes
    if request.status_code == 403:
        raise Exception('Too many requests in a short amount of time!\nYou\'ve hit the non-documented anti-abuse limit!')
    raise Exception('recursive_loc() has failed with a', request.status_code, request.text, QUERY_COUNT)


def loc_counter_one_repo(owner, repo_name, data, cache_comment, history, addition_total, deletion_total, my_commits):
    """
    Recursively call recursive_loc (since GraphQL can only search 100 commits at a time) 
    only adds the LOC value of commits authored by me
    """
    for node in history['edges']:
        if node['node']['author']['user'] == OWNER_ID:
            my_commits += 1
            addition_total += node['node']['additions']
            deletion_total += node['node']['deletions']

    if history['edges'] == [] or not history['pageInfo']['hasNextPage']:
        return addition_total, deletion_total, my_commits
    else: return recursive_loc(owner, repo_name, data, cache_comment, addition_total, deletion_total, my_commits, history['pageInfo']['endCursor'])


def loc_query(owner_affiliation, comment_size=0, force_cache=False, cursor=None, edges=[]):
    """
    Uses GitHub's GraphQL v4 API to query all the repositories I have access to (with respect to owner_affiliation)
    Queries 60 repos at a time, because larger queries give a 502 timeout error and smaller queries send too many
    requests and also give a 502 error.
    Returns the total number of lines of code in all repositories
    """
    query_count('loc_query')
    query = '''
    query ($owner_affiliation: [RepositoryAffiliation], $login: String!, $cursor: String) {
        user(login: $login) {
            repositories(first: 60, after: $cursor, ownerAffiliations: $owner_affiliation) {
            edges {
                node {
                    ... on Repository {
                        nameWithOwner
                        defaultBranchRef {
                            target {
                                ... on Commit {
                                    history {
                                        totalCount
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
                pageInfo {
                    endCursor
                    hasNextPage
                }
            }
        }
    }'''
    variables = {'owner_affiliation': owner_affiliation, 'login': USER_NAME, 'cursor': cursor}
    request = request_maker(loc_query.__name__, query, variables)
    if request.json()['data']['user']['repositories']['pageInfo']['hasNextPage']:   # If repository data has another page
        edges += request.json()['data']['user']['repositories']['edges']            # Add on to the LoC count
        return loc_query(owner_affiliation, comment_size, force_cache, request.json()['data']['user']['repositories']['pageInfo']['endCursor'], edges)
    else:
        return cache_builder(edges + request.json()['data']['user']['repositories']['edges'], comment_size, force_cache)


def update_readme(follower_data, star_data, repo_data, contrib_data, total_loc, commit_data):
    content = (
        "# Profile Readme\n\n"
        f"Last updated: {datetime.now().isoformat()}\n\n"
        "Hello from profile-readme-template!\n"
        f"Follower data: {follower_data}\n"
        f"Star data: {star_data}\n"
        f"Repo data: {repo_data}\n"
        f"Contrib data: {contrib_data}\n"
        f"Total Loc data: {total_loc}\n"
        f"Commit data: {commit_data}\n"
    )
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(content)



def svg_overwrite(filename, age_data, commit_data, star_data, repo_data, contrib_data, follower_data, loc_data, user_created_at=None, make_github_safe=True):
    """
    Parse SVG and update elements with commits, stars, repositories, followers, and LOC.
    Uses XML parsing to avoid corrupting layout and adds dot justification.
    """
    tree = etree.parse(filename)
    root = tree.getroot()

    justify_format(root, 'commit_data', commit_data, 22)
    justify_format(root, 'star_data', star_data, 14)
    justify_format(root, 'repo_data', repo_data, 6)
    justify_format(root, 'contrib_data', contrib_data)
    justify_format(root, 'follower_data', follower_data, 10)

    # loc_data is expected [add, del, net, cached?]
    try:
        loc_add = loc_data[0]
        loc_del = loc_data[1]
        loc_net = loc_data[2]
    except Exception:
        loc_add = loc_del = loc_net = 0

    justify_format(root, 'loc_data', loc_net, 9)
    justify_format(root, 'loc_add', loc_add)
    justify_format(root, 'loc_del', loc_del, 7)

    # Uptime / Age line
    if age_data is not None:
        find_and_replace(root, 'uptime_data', age_data)

    # ------------------------------------------------------------
    # Extended sections: Productivity, Streaks, Yearly Trend
    # ------------------------------------------------------------
    # Embed GIF as data URI if present
    try:
        gif_elem = root.find(".//*[@id='profile_gif']")
        import glob, base64, random
        # Determine preferred image: ascii-art.png (in root or gifs/), else fallback random gif
        preferred_paths = ['ascii-art.png', 'gifs/ascii-art.png', 'assets/ascii-art.png']
        candidate = None
        for p in preferred_paths:
            if os.path.exists(p):
                candidate = p
                break
        if candidate is None:
            # fallback to existing href or random gif
            if gif_elem is not None:
                candidate = gif_elem.attrib.get('href') or gif_elem.attrib.get('{http://www.w3.org/1999/xlink}href')
            if not candidate or not os.path.exists(candidate):
                gif_matches = glob.glob('gifs/*.gif')
                candidate = random.choice(gif_matches) if gif_matches else None

        if candidate and os.path.exists(candidate):
            # Ensure an <image> element exists; create if missing and place after the left panel rect
            if gif_elem is None:
                gif_elem = etree.Element('{http://www.w3.org/2000/svg}image', attrib={'id': 'profile_gif'})
                # Insert after the first left-panel rect
                children = list(root)
                insert_idx = 0
                for idx, child in enumerate(children):
                    if child.tag.endswith('rect') and child.attrib.get('x') == '15' and child.attrib.get('y') == '15' and child.attrib.get('width') == '360' and child.attrib.get('height') == '850':
                        insert_idx = idx + 1
                        break
                root.insert(insert_idx, gif_elem)

            # Encode image as data URI (png or gif)
            ext = os.path.splitext(candidate)[1].lower()
            mime = 'image/png' if ext == '.png' else 'image/gif'
            with open(candidate, 'rb') as imf:
                b64 = base64.b64encode(imf.read()).decode('ascii')
            data_uri = f"data:{mime};base64,{b64}"

            # Set hrefs
            gif_elem.set('{http://www.w3.org/1999/xlink}href', data_uri)
            gif_elem.set('href', data_uri)
            # Ensure it fits inside the container and is clipped to rounded corners
            gif_elem.set('x', '15')
            gif_elem.set('y', '15')
            gif_elem.set('width', '360')
            gif_elem.set('height', '850')
            gif_elem.set('preserveAspectRatio', 'xMidYMid meet')
            # Ensure clipPath exists
            defs = root.find('.//{http://www.w3.org/2000/svg}defs')
            if defs is None:
                defs = etree.SubElement(root, '{http://www.w3.org/2000/svg}defs')
            clip = root.find(".//*[@id='gif_clip']")
            if clip is None:
                clip = etree.SubElement(defs, '{http://www.w3.org/2000/svg}clipPath', attrib={'id': 'gif_clip'})
                etree.SubElement(clip, '{http://www.w3.org/2000/svg}rect', attrib={'x': '15', 'y': '15', 'width': '360', 'height': '850', 'rx': '10'})
            gif_elem.set('clip-path', 'url(#gif_clip)')
    except Exception:
        pass

    try:
        from extra_feature import analyze_productive_times, get_streak_and_average, get_yearly_contribution_trend

        # Productivity Insights
        from datetime import datetime
        start_of_year = datetime(datetime.now().year, 1, 1).isoformat() + 'Z'
        today_iso = datetime.now().isoformat() + 'Z'

        # Query contribution days for productivity
        query = '''
        query($login: String!, $from: DateTime!, $to: DateTime!) {
            user(login: $login) {
                contributionsCollection(from: $from, to: $to) {
                    contributionCalendar {
                        weeks { contributionDays { date contributionCount } }
                    }
                }
            }
        }'''
        variables = {'login': USER_NAME, 'from': start_of_year, 'to': today_iso}
        req = request_maker('svg_overwrite_days', query, variables)
        weeks = req.json()['data']['user']['contributionsCollection']['contributionCalendar']['weeks']
        all_days = []
        for week in weeks:
            all_days.extend(week['contributionDays'])

        productivity = analyze_productive_times(all_days)
        most = productivity['most_productive_day']
        least = productivity['least_productive_day']
        justify_format(root, 'most_productive', f"{most['name']} ({most['average']} avg)")
        justify_format(root, 'least_productive', f"{least['name']} ({least['average']} avg)")

        weekday_ids = {
            0: 'monday_avg', 1: 'tuesday_avg', 2: 'wednesday_avg',
            3: 'thursday_avg', 4: 'friday_avg', 5: 'saturday_avg', 6: 'sunday_avg'
        }
        for day_num, elem_id in weekday_ids.items():
            avg = productivity['weekday_stats'][day_num]['average']
            justify_format(root, elem_id, f"{avg} avg")

        # Contribution Streaks
        streaks = get_streak_and_average(USER_NAME, start_of_year, today_iso)
        justify_format(root, 'current_streak', f"{streaks['current_streak']} days")
        justify_format(root, 'longest_streak', f"{streaks['longest_streak']} days")
        justify_format(root, 'average_per_day', f"{streaks['average_per_day']}")
        justify_format(root, 'total_contributions', f"{streaks['total_contributions']}")

        # Yearly Contribution Trend
        if user_created_at is not None:
            yearly = get_yearly_contribution_trend(USER_NAME, user_created_at)
            for y in yearly:
                year_id = f"year_{y['year']}"
                contributions = y['contributions']
                growth = y.get('growth')
                if growth is None:
                    value = f"{contributions} commits"
                else:
                    sign = '+' if growth > 0 else ('-' if growth < 0 else '±')
                    value = f"{contributions} commits ({sign}{abs(growth)}%)"
                find_and_replace(root, year_id, value)
    except Exception:
        # Leave sections untouched if data fetch fails
        pass

    tree.write(filename, encoding='utf-8', xml_declaration=True)

    # Optionally create a GitHub-safe copy without embedded <image> (blocked by GitHub sanitizer)
    if make_github_safe:
        try:
            safe_tree = etree.parse(filename)
            safe_root = safe_tree.getroot()
            # Remove all image elements (esp. embedded data URIs)
            for elem in list(safe_root.iter()):
                if elem.tag.endswith('image'):
                    parent = elem.getparent() if hasattr(elem, 'getparent') else None
                    # xml.etree.ElementTree lacks getparent; fallback to rebuild
            # Fallback: rebuild tree without <image> by searching recursively
            def remove_images(node):
                to_remove = [child for child in list(node) if child.tag.endswith('image')]
                for child in to_remove:
                    node.remove(child)
                for child in list(node):
                    remove_images(child)
            remove_images(safe_root)

            github_filename = filename.replace('.svg', '-github.svg')
            safe_tree.write(github_filename, encoding='utf-8', xml_declaration=True)
        except Exception:
            pass


def justify_format(root, element_id, new_text, length=0):
    """
    Update element text and adjust preceding dots span to keep right alignment.
    """
    if isinstance(new_text, int):
        new_text = f"{'{:,}'.format(new_text)}"
    new_text = str(new_text)

    find_and_replace(root, element_id, new_text)

    just_len = max(0, length - len(new_text))
    if just_len <= 2:
        dot_map = {0: '', 1: ' ', 2: '. '}
        dot_string = dot_map[just_len]
    else:
        dot_string = ' ' + ('.' * just_len) + ' '

    find_and_replace(root, f"{element_id}_dots", dot_string)


def find_and_replace(root, element_id, new_text):
    """
    Find the element in the SVG by id and replace its text.
    """
    element = root.find(f".//*[@id='{element_id}']")
    if element is not None:
        element.text = str(new_text)


def main():
    global OWNER_ID
    
    user_data, user_time = perf_counter(user_getter, USER_NAME)
    OWNER_ID, acc_date = user_data

    follower_data, follower_time = perf_counter(follower_getter, USER_NAME)
    star_data, star_time = perf_counter(graph_repos_stars, 'stars', ['OWNER'])
    repo_data, repo_time = perf_counter(graph_repos_stars, 'repos', ['OWNER'])
    contrib_data, contrib_time = perf_counter(graph_repos_stars, 'repos', ['OWNER', 'COLLABORATOR', 'ORGANIZATION_MEMBER'])
    total_loc, loc_time = perf_counter(loc_query, ['OWNER', 'COLLABORATOR', 'ORGANIZATION_MEMBER'], 7)
    commit_data, commit_time = perf_counter(commit_counter, 7)

    print("Follower data: ", follower_data)
    print("Follower Time: ", follower_time)
    print("Star data: ", star_data)
    print("Star Time", star_time)
    print("Repo Data", repo_data)
    print("Repo Time", repo_time)
    print("Contrib Data", contrib_data)
    print("Contrib Time: ", contrib_time)
    print("Total loc: ", total_loc)
    print("Loc time: ", loc_time)
    print("Commit data: ", commit_data)
    print("Commit time: ", commit_time) 

    # Compute age (uptime) from fixed DOB: June 7, 2003
    from datetime import date
    dob = date(2003, 6, 7)
    today = date.today()
    years = today.year - dob.year - (1 if (today.month, today.day) < (dob.month, dob.day) else 0)
    last_birthday_year = today.year if (today.month, today.day) >= (dob.month, dob.day) else today.year - 1
    from datetime import date as _date
    last_birthday = _date(last_birthday_year, dob.month, dob.day)
    days = (today - last_birthday).days
    age_str = f"{years} years, {days} days"

    svg_overwrite(
        filename='profile-card-github.svg',
        age_data=age_str,
        commit_data=commit_data,
        star_data=star_data,
        repo_data=repo_data,
        contrib_data=contrib_data,
        follower_data=follower_data,
        loc_data=total_loc,
        user_created_at=acc_date,
    )

    
if __name__ == "__main__":
    main()
