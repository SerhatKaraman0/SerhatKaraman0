import os
import requests
from datetime import datetime
from collections import defaultdict
from main import query_count

def get_headers():
    """Get headers with access token"""
    return {'authorization': 'token ' + os.environ.get('ACCESS_TOKEN', '')}

def request_maker(func_name, query, variables):
    """Returns a request, or raises an Exception if the response does not succeed."""
    request = requests.post('https://api.github.com/graphql', json={'query': query, 'variables': variables}, headers=get_headers())
    if request.status_code == 200:
        return request
    raise Exception(func_name, ' has failed with a', request.status_code, request.text)


def get_top_languages(login, limit=5):
    """Get top programming languages by LOC"""
    query = '''
    query($login: String!) {
        user(login: $login) {
            repositories(first: 100, ownerAffiliations: OWNER) {
                nodes {
                    languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
                        edges {
                            size
                            node {
                                name
                                color
                            }
                        }
                    }
                }
            }
        }
    }'''
    
    variables = {'login': login}
    request = request_maker(get_top_languages.__name__, query, variables)
    
    # Aggregate all languages across repos
    language_stats = defaultdict(lambda: {'size': 0, 'color': '#000000'})
    
    repositories = request.json()['data']['user']['repositories']['nodes']
    
    for repo in repositories:
        if repo['languages']['edges']:
            for lang_edge in repo['languages']['edges']:
                lang_name = lang_edge['node']['name']
                lang_size = lang_edge['size']
                lang_color = lang_edge['node']['color'] or '#000000'
                
                language_stats[lang_name]['size'] += lang_size
                language_stats[lang_name]['color'] = lang_color
    
    # Calculate total size for percentages
    total_size = sum(int(lang['size']) for lang in language_stats.values())
    
    # Sort by size and get top N
    sorted_languages = sorted(
        language_stats.items(),
        key=lambda x: x[1]['size'],
        reverse=True
    )[:limit]
    
    # Format results with percentages
    results = []
    for lang_name, lang_data in sorted_languages:
        lang_size = int(lang_data['size'])
        percentage = (lang_size / total_size * 100) if total_size > 0 else 0
        results.append({
            'name': lang_name,
            'size': lang_size,
            'color': lang_data['color'],
            'percentage': round(percentage, 1)
        })
    
    return results


def format_language_bar(language_data):
    """Create visual progress bar for language statistics"""
    output = []
    for lang in language_data:
        # Create progress bar (20 characters total)
        filled = int(lang['percentage'] / 5)  # Each block = 5%
        empty = 20 - filled
        bar = '█' * filled + '░' * empty
        
        output.append(f"{lang['name']:<12} {bar} {lang['percentage']:>5.1f}%")
    
    return '\n'.join(output)


def analyze_productive_times(contribution_days):
    """Analyze when you're most productive"""
    from datetime import datetime
    
    # Group by weekday (0=Monday, 6=Sunday)
    weekday_counts = {i: [] for i in range(7)}
    weekday_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    for day in contribution_days:
        date_obj = datetime.strptime(day['date'], '%Y-%m-%d')
        weekday = date_obj.weekday()
        weekday_counts[weekday].append(day['contributionCount'])
    
    # Calculate averages for each day
    weekday_averages = {}
    for day_num, counts in weekday_counts.items():
        if counts:
            avg = sum(counts) / len(counts)
            total = sum(counts)
            weekday_averages[day_num] = {
                'name': weekday_names[day_num],
                'average': round(avg, 2),
                'total': total,
                'days_with_activity': sum(1 for c in counts if c > 0)
            }
        else:
            weekday_averages[day_num] = {
                'name': weekday_names[day_num],
                'average': 0,
                'total': 0,
                'days_with_activity': 0
            }
    
    # Find most and least productive days
    sorted_by_avg = sorted(
        weekday_averages.items(),
        key=lambda x: x[1]['average'],
        reverse=True
    )
    
    most_productive = sorted_by_avg[0][1]
    least_productive = sorted_by_avg[-1][1]
    
    # Analyze time distribution (categorize by contribution count)
    low_activity_days = sum(1 for day in contribution_days if 0 < day['contributionCount'] <= 3)
    medium_activity_days = sum(1 for day in contribution_days if 3 < day['contributionCount'] <= 10)
    high_activity_days = sum(1 for day in contribution_days if day['contributionCount'] > 10)
    
    return {
        'most_productive_day': most_productive,
        'least_productive_day': least_productive,
        'weekday_stats': weekday_averages,
        'activity_distribution': {
            'low': low_activity_days,
            'medium': medium_activity_days,
            'high': high_activity_days
        }
    }


def format_productivity_report(productivity_data):
    """Format productivity analysis into readable text"""
    report = []
    report.append("📊 Productivity Insights:")
    report.append("")
    
    most = productivity_data['most_productive_day']
    least = productivity_data['least_productive_day']
    
    report.append(f"  🏆 Most productive:  {most['name']} (avg {most['average']} commits)")
    report.append(f"  😴 Least productive: {least['name']} (avg {least['average']} commits)")
    report.append("")
    report.append("  Weekly breakdown:")
    
    for day_num in range(7):
        stats = productivity_data['weekday_stats'][day_num]
        bar_length = int(stats['average'] * 2) if stats['average'] > 0 else 0
        bar = '▓' * bar_length + '░' * max(0, 20 - bar_length)
        report.append(f"    {stats['name']:<10} {bar[:20]} {stats['average']:>5.1f} avg")
    
    return '\n'.join(report)


def get_yearly_contribution_trend(login, user_created_at):
    """Get contribution trend over years"""
    from datetime import datetime
    
    # Parse user creation date
    created_year = datetime.fromisoformat(user_created_at.replace('Z', '+00:00')).year
    current_year = datetime.now().year
    
    yearly_stats = []
    
    for year in range(created_year, current_year + 1):
        start_date = f"{year}-01-01T00:00:00Z"
        end_date = f"{year}-12-31T23:59:59Z"
        
        query = '''
        query($login: String!, $from: DateTime!, $to: DateTime!) {
            user(login: $login) {
                contributionsCollection(from: $from, to: $to) {
                    contributionCalendar {
                        totalContributions
                    }
                }
            }
        }'''
        
        variables = {'login': login, 'from': start_date, 'to': end_date}
        request = request_maker(get_yearly_contribution_trend.__name__, query, variables)
        
        total = request.json()['data']['user']['contributionsCollection']['contributionCalendar']['totalContributions']
        yearly_stats.append({'year': year, 'contributions': total})
    
    # Calculate growth percentages
    for i in range(1, len(yearly_stats)):
        prev_year = yearly_stats[i - 1]['contributions']
        curr_year = yearly_stats[i]['contributions']
        
        if prev_year > 0:
            growth = ((curr_year - prev_year) / prev_year) * 100
        else:
            growth = 100 if curr_year > 0 else 0
        
        yearly_stats[i]['growth'] = round(growth, 1)
    
    # First year has no growth comparison
    yearly_stats[0]['growth'] = None
    
    return yearly_stats


def format_yearly_trend(yearly_stats):
    """Format yearly contribution trend with visual bars"""
    if not yearly_stats:
        return "No contribution data available"
    
    max_contributions = max(year['contributions'] for year in yearly_stats)
    
    output = []
    output.append("📈 Yearly Contribution Trend:")
    output.append("")
    
    for year_data in yearly_stats:
        year = year_data['year']
        contributions = year_data['contributions']
        growth = year_data['growth']
        
        # Create progress bar (10 blocks max)
        if max_contributions > 0:
            bar_length = int((contributions / max_contributions) * 10)
        else:
            bar_length = 0
        
        bar = '▓' * bar_length + '░' * (10 - bar_length)
        
        # Format growth indicator
        if growth is not None:
            if growth > 0:
                growth_str = f"(+{growth}%)"
            elif growth < 0:
                growth_str = f"({growth}%)"
            else:
                growth_str = "(±0%)"
        else:
            growth_str = ""
        
        output.append(f"  {year}: {bar} {contributions:,} commits {growth_str}")
    
    return '\n'.join(output)


# Example usage function
def demo_all_features(login, user_created_at):
    """Demonstrate all features"""
    print("=" * 60)
    print("GitHub Profile Statistics")
    print("=" * 60)
    print()
    
    # Top Languages
    print("🔤 Top Programming Languages:")
    print()
    languages = get_top_languages(login, limit=5)
    print(format_language_bar(languages))
    print()
    
    # Get contribution data for productivity analysis
    from datetime import datetime
    start_of_year = datetime(datetime.now().year, 1, 1).isoformat() + 'Z'
    today = datetime.now().isoformat() + 'Z'
    
    query = '''
    query($login: String!, $from: DateTime!, $to: DateTime!) {
        user(login: $login) {
            contributionsCollection(from: $from, to: $to) {
                contributionCalendar {
                    weeks {
                        contributionDays {
                            date
                            contributionCount
                        }
                    }
                }
            }
        }
    }'''
    
    variables = {'login': login, 'from': start_of_year, 'to': today}
    request = request_maker('demo', query, variables)
    
    weeks = request.json()['data']['user']['contributionsCollection']['contributionCalendar']['weeks']
    all_days = []
    for week in weeks:
        all_days.extend(week['contributionDays'])
    
    # Productivity Analysis
    print()
    productivity = analyze_productive_times(all_days)
    print(format_productivity_report(productivity))
    print()
    
    # Yearly Trend
    print()
    yearly = get_yearly_contribution_trend(login, user_created_at)
    print(format_yearly_trend(yearly))
    print()
    print("=" * 60)

def calculate_streak(contribution_days):
    """
    Calculate current and longest contribution streak
    Returns: (current_streak, longest_streak)
    """
    current_streak = 0
    longest_streak = 0
    temp_streak = 0
    
    # Sort days by date (should already be sorted, but just in case)
    sorted_days = sorted(contribution_days, key=lambda x: x['date'])
    
    from datetime import datetime, timedelta
    today = datetime.now().date()
    
    for i, day_data in enumerate(sorted_days):
        day_date = datetime.strptime(day_data['date'], '%Y-%m-%d').date()
        
        if day_data['contributionCount'] > 0:
            temp_streak += 1
            longest_streak = max(longest_streak, temp_streak)
            
            # Check if this is part of current streak (must reach today or yesterday)
            if day_date == today or day_date == today - timedelta(days=1):
                current_streak = temp_streak
        else:
            temp_streak = 0  # Reset on day with no contributions
    
    return current_streak, longest_streak


def calculate_average_commits_per_day(contribution_calendar, from_date, to_date):
    """
    Calculate average commits per day
    Returns: average commits per day (float)
    """
    from datetime import datetime
    
    total_contributions = contribution_calendar['totalContributions']
    
    # Calculate total days in range
    start = datetime.fromisoformat(from_date.replace('Z', '+00:00'))
    end = datetime.fromisoformat(to_date.replace('Z', '+00:00'))
    total_days = (end - start).days + 1
    
    average = total_contributions / total_days if total_days > 0 else 0
    
    return round(average, 2)


def get_streak_and_average(login, from_date, to_date):
    """
    Get commit streak and average commits per day
    """
    query_count('graph_commits')
    query = '''
    query($login: String!, $from: DateTime!, $to: DateTime!) {
        user(login: $login) {
            contributionsCollection(from: $from, to: $to) {
                contributionCalendar {
                    totalContributions
                    weeks {
                        contributionDays {
                            date
                            contributionCount
                        }
                    }
                }
            }
        }
    }'''
    
    variables = {'login': login, 'from': from_date, 'to': to_date}
    request = request_maker(get_streak_and_average.__name__, query, variables)
    
    data = request.json()['data']['user']['contributionsCollection']
    contribution_calendar = data['contributionCalendar']
    
    # Flatten weeks into a single list of days
    all_days = []
    for week in contribution_calendar['weeks']:
        all_days.extend(week['contributionDays'])
    
    current_streak, longest_streak = calculate_streak(all_days)
    average_per_day = calculate_average_commits_per_day(contribution_calendar, from_date, to_date)
    
    return {
        'current_streak': current_streak,
        'longest_streak': longest_streak,
        'average_per_day': average_per_day,
        'total_contributions': contribution_calendar['totalContributions']
    }

def main():
    """Example main function - update with your GitHub username"""
    login = "SerhatKaraman0"
    
    # Get user info to get created date
    query = '''
    query($login: String!) {
        user(login: $login) {
            createdAt
        }
    }'''
    
    variables = {'login': login}
    request = request_maker('main', query, variables)
    user_created_at = request.json()['data']['user']['createdAt']
    
    demo_all_features(login, user_created_at)
    start_of_year = datetime(2025, 1, 1).isoformat() + 'Z'
    today = datetime.now().isoformat() + 'Z'

    stats = get_streak_and_average("SerhatKaraman0", start_of_year, today)

    print(f"Current streak: {stats['current_streak']} days")
    print(f"Longest streak: {stats['longest_streak']} days")
    print(f"Average commits/day: {stats['average_per_day']}")
    print(f"Total contributions: {stats['total_contributions']}")

if __name__ == '__main__':
    from dotenv import load_dotenv
    load_dotenv()
    main()