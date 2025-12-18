from jira import JIRA
from datetime import datetime, timedelta
import pandas as pd
from collections import defaultdict
import time



jira_url = '***********'


username = '*************'
api_token = '*****************'



jira = JIRA(server=jira_url, basic_auth=(username, api_token))



date_14_days_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')


project_list = ["*****", "*****"]


projects_str = ", ".join(f'"{p}"' for p in project_list)


jql_query = (
    f'project IN ({projects_str}) '
    f'AND updated >= "{date_14_days_ago}" '
    f'AND issuetype NOT IN ("Story") '
    f'AND (labels = "agents_shared_visibility" OR component = "3.0 Report Request") '
    f'AND status NOT IN ("Won\'t Fix")'
    f'AND assignee = "Vladyslav Atapov"'
)

batch_size = 100
start_at = 0


issue_data = []


while True:
    issues = jira.search_issues(jql_query, startAt=start_at, maxResults=batch_size, expand='changelog')
    if not issues:
        break

    for issue in issues:
        issue_row = {
            "Ticket Key": issue.key,
            "Summary": issue.fields.summary,
            "Status": issue.fields.status.name,
            "Assignee": issue.fields.assignee.displayName if issue.fields.assignee else 'Unassigned'
        }


        created_time = datetime.strptime(issue.fields.created.split('.')[0], '%Y-%m-%dT%H:%M:%S')
        issue_row["Created"] = created_time.strftime('%Y-%m-%d %H:%M:%S')


        changelog = issue.changelog

        # Request Complexity
        complexity = 3
        for history in changelog.histories:
            for item in history.items:
                if item.field == 'Request Complexity':
                    try:
                        complexity = int(item.toString)
                    except:
                        complexity = 3
                    break
            if complexity != 3:
                break
        issue_row["Request Complexity"] = complexity


        # Weekends between two dates
        def count_weekend_days(start_date, end_date):
            count = 0
            current_date = start_date
            while current_date <= end_date:
                if current_date.weekday() >= 5:  # Monday to Friday are 0 to 4
                    count += 1
                current_date += timedelta(days=1)
            return count


        # Assignee time
        assignee_time = None
        for history in changelog.histories:
            for item in history.items:
                if item.field == 'assignee':
                    assignee_time = datetime.strptime(history.created.split('.')[0], '%Y-%m-%dT%H:%M:%S')
                    break
            if assignee_time:
                break

        # QA time
        qa_time = None
        for history in changelog.histories:
            for item in history.items:
                if item.field == 'status' and item.toString == 'In QA' or issue.key.startswith('CAAB') and item.field == 'status' and item.toString == 'Done':
                    qa_time = datetime.strptime(history.created.split('.')[0], '%Y-%m-%dT%H:%M:%S')
                    break
            if qa_time:
                break

        # Time On Hold
        total_on_hold = timedelta(0)
        on_hold_start = None
        for history in reversed(changelog.histories):
            for item in history.items:
                if item.field == 'status' and item.toString == 'On Hold':
                    on_hold_start = datetime.strptime(history.created.split('.')[0], '%Y-%m-%dT%H:%M:%S')
                elif item.field == 'status' and item.fromString == 'On Hold' and on_hold_start:
                    on_hold_end = datetime.strptime(history.created.split('.')[0], '%Y-%m-%dT%H:%M:%S')
                    total_on_hold += on_hold_end - on_hold_start
                    total_on_hold_subtracting_weekends = count_weekend_days(on_hold_start, on_hold_end)
                    total_on_hold = total_on_hold - timedelta(days=total_on_hold_subtracting_weekends)
                    on_hold_start = None

        # Time Up Next
        total_up_next = timedelta(0)
        up_next_start = None
        for history in reversed(changelog.histories):
            for item in history.items:
                if item.field == 'status' and item.toString == 'Up Next':
                    up_next_start = datetime.strptime(history.created.split('.')[0], '%Y-%m-%dT%H:%M:%S')
                elif item.field == 'status' and item.fromString == 'Up Next' and up_next_start:
                    up_next_end = datetime.strptime(history.created.split('.')[0], '%Y-%m-%dT%H:%M:%S')
                    total_up_next += up_next_end - up_next_start
                    total_up_next_subtracting_weekends = count_weekend_days(up_next_start, up_next_end)
                    total_up_next = total_up_next - timedelta(days=total_up_next_subtracting_weekends)
                    up_next_start = None

        # Time Pending progress
        total_pending_progress = timedelta(0)
        pending_progress_start = None
        for history in reversed(changelog.histories):
            for item in history.items:
                if item.field == 'status' and item.toString == 'Pending progress':
                    pending_progress_start = datetime.strptime(history.created.split('.')[0], '%Y-%m-%dT%H:%M:%S')
                elif item.field == 'status' and item.fromString == 'Pending progress' and pending_progress_start:
                    pending_progress_end = datetime.strptime(history.created.split('.')[0], '%Y-%m-%dT%H:%M:%S')
                    total_pending_progress += pending_progress_end - pending_progress_start
                    total_pending_progress_subtracting_weekends = count_weekend_days(pending_progress_start, pending_progress_end)
                    total_pending_progress = total_pending_progress - timedelta(days=total_pending_progress_subtracting_weekends)
                    pending_progress_start = None

        # Time In Review
        total_in_review = timedelta(0)
        in_review_start = None
        for history in reversed(changelog.histories):
            for item in history.items:
                if item.field == 'status' and item.toString == 'In Review':
                    in_review_start = datetime.strptime(history.created.split('.')[0], '%Y-%m-%dT%H:%M:%S')
                elif item.field == 'status' and item.fromString == 'In Review' and in_review_start:
                    in_review_end = datetime.strptime(history.created.split('.')[0],'%Y-%m-%dT%H:%M:%S')
                    total_in_review += in_review_end - in_review_start
                    total_in_review_subtracting_weekends = count_weekend_days(in_review_start, in_review_end)
                    total_in_review = total_in_review - timedelta(days=total_in_review_subtracting_weekends)
                    in_review_start = None

        # Time Done (CAAB)
        total_in_done = timedelta(0)
        in_done_start = None
        for history in reversed(changelog.histories):
            for item in history.items:
                if issue.key.startswith('CAAB') and item.field == 'status' and item.toString == 'Done':
                    in_done_start = datetime.strptime(history.created.split('.')[0],'%Y-%m-%dT%H:%M:%S')
                elif issue.key.startswith('CAAB') and item.field == 'status' and item.fromString == 'Done' and in_done_start:
                    in_done_end = datetime.strptime(history.created.split('.')[0],'%Y-%m-%dT%H:%M:%S')
                    total_in_done += in_done_end - in_done_start
                    total_in_done_subtracting_weekends = count_weekend_days(in_done_start, in_done_end)
                    total_in_done = total_in_done - timedelta(days=total_in_done_subtracting_weekends)
                    in_done_start = None

        duration = timedelta(0)
        weekend_days = 0

        if assignee_time and qa_time:
            duration = qa_time - assignee_time
            weekend_days = count_weekend_days(assignee_time, qa_time)
            total_duration = duration - total_on_hold - total_up_next - total_in_done - timedelta(days=weekend_days)
            if total_duration > total_in_review:
                total_duration = total_duration - total_in_review
            else:
                total_duration = total_duration
        else:
            total_duration = timedelta(0)

        # Formatting the duration
        if total_duration >= timedelta(0):
            total_seconds = int(total_duration.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            issue_row["Assigned → QA Duration"] = f"{hours:02}:{minutes:02}:{seconds:02}"
        else:
            total_seconds = int(timedelta(0).total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            issue_row["Assigned → QA Duration"] = f"{hours:02}:{minutes:02}:{seconds:02}"

        # Time in Progress
        total_in_progress = timedelta(0)
        in_progress_start = None
        for history in reversed(changelog.histories):
            for item in history.items:
                if item.field == 'status' and item.toString == 'In Progress':
                    in_progress_start = datetime.strptime(history.created.split('.')[0], '%Y-%m-%dT%H:%M:%S')
                elif item.field == 'status' and item.fromString == 'In Progress' and in_progress_start:
                    in_progress_end = datetime.strptime(history.created.split('.')[0], '%Y-%m-%dT%H:%M:%S')
                    total_in_progress += in_progress_end - in_progress_start
                    in_progress_start = None
        total_seconds = int(total_in_progress.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        issue_row["In Progress Duration"] = f"{hours:02}:{minutes:02}:{seconds:02}"


        issue_data.append(issue_row)

        print(f"key: {issue.key}")
        print(f"summary: {issue.fields.summary}")
        print(f"status: {issue.fields.status.name}")
        print(f"Assignee: {issue.fields.assignee.displayName if issue.fields.assignee else 'Unassigned'}")
        print(f"Created date: {issue.fields.created}")
        print(f"In Progress Duration: {issue_row["In Progress Duration"]}")
        print(f"Assigned → QA Duration: {issue_row["Assigned → QA Duration"]}")
        print(f"assignee_time: {assignee_time}")
        print(f"qa_time: {qa_time}")
        print(f"total_on_hold: {total_on_hold}")
        print(f"total_up_next: {total_up_next}")
        print(f"total_duration: {total_duration}")
        print(f"weekend_days: {timedelta(days=weekend_days)}")
        print(f"total_pending_progress: {total_pending_progress}")
        print(f"duration: {duration}")
        print(f"total_in_review: {total_in_review}")
        print(f"total_in_done: {total_in_done}")
        print("-" * 50)

    start_at += batch_size


df_all = pd.DataFrame(issue_data)


def parse_duration(d):
    h, m, s = map(int, d.split(":"))
    return timedelta(hours=h, minutes=m, seconds=s)

df_all["Assigned → QA Duration"] = df_all["Assigned → QA Duration"].apply(parse_duration)
df_all["In Progress Duration"] = df_all["In Progress Duration"].apply(parse_duration)


main_allowed = ["Open", "Pending progress", "In Progress", "To Do", "In QA"]
avg_allowed = main_allowed + ["In Review","Closed"]

df_main = df_all[df_all["Status"].isin(main_allowed)].copy()
df_avg = df_all[df_all["Status"].isin(avg_allowed)].copy()


team_map = {
    "*****************"
}

df_main["Team"] = df_main["Assignee"].map(team_map).fillna("Unassigned")
df_avg["Team"]  = df_avg["Assignee"].map(team_map).fillna("Unassigned")


weight_map = {1: 0.5, 2: 0.75, 3: 1, 4: 2, 5: 3}
df_main["Weight"] = df_main["Request Complexity"].map(weight_map)
df_avg["Weight"]  = df_avg["Request Complexity"].map(weight_map)


summary = (
    df_main
    .groupby(["Team", "Assignee"])
    .agg(
        Ticket_Count       = ("Ticket Key",             "count"),
        Assigned_to_QA_td  = ("Assigned → QA Duration", "sum"),
        In_Progress_td     = ("In Progress Duration",   "sum"),
    )
    .reset_index()
)


complexity_counts = (
    df_main
    .groupby(["Assignee", "Request Complexity"])
    .size()
    .unstack(fill_value=0)
)
for lvl in range(1, 6):
    if lvl not in complexity_counts.columns:
        complexity_counts[lvl] = 0
complexity_counts = (
    complexity_counts
    .rename(columns=lambda x: f"CMPX {x}")
    .reset_index()
)


weight_per_assignee = (
    df_main
    .groupby("Assignee")["Weight"]
    .sum()
    .reset_index()
    .rename(columns={"Weight": "Coef_Sum"})
)


def format_td(td):
    total_seconds = int(td.total_seconds())
    h = total_seconds // 3600
    m = (total_seconds % 3600) // 60
    s = total_seconds % 60
    return f"{h:02}:{m:02}:{s:02}"

summary["Assigned_to_QA"] = summary["Assigned_to_QA_td"].apply(format_td)
summary["In_Progress"]    = summary["In_Progress_td"].apply(format_td)


summary = summary.drop(columns=["Assigned_to_QA_td", "In_Progress_td"])


merged_live = pd.merge(summary, complexity_counts, on="Assignee", how="left")
live_summary = pd.merge(merged_live, weight_per_assignee, on="Assignee", how="left")


team_totals_live = (
    live_summary
    .groupby("Team")["Ticket_Count"]
    .sum()
    .reset_index()
    .rename(columns={"Ticket_Count": "Team_Total_Tickets"})
)
team_totals_complex_live = (
    live_summary
    .groupby("Team")["Coef_Sum"]
    .sum()
    .reset_index()
    .rename(columns={"Coef_Sum": "Team_Total_Complex"})
)

live_summary = pd.merge(live_summary, team_totals_live, on="Team", how="left")
live_summary = pd.merge(live_summary, team_totals_complex_live, on="Team", how="left")


live_summary["Workload"] = (
    (live_summary["Coef_Sum"] / live_summary["Team_Total_Complex"]) * 100
).round(2).astype(str) + " %"


df_avg["Assigned → QA Duration"] = df_avg["Assigned → QA Duration"].apply(
    lambda td: td if td != timedelta(0) else pd.NaT
)
df_avg["In Progress Duration"] = df_avg["In Progress Duration"].apply(
    lambda td: td if td != timedelta(0) else pd.NaT
)


avg_group = (
    df_avg
    .groupby(["Team", "Assignee"])
    .agg(
        Avg_Assigned_to_QA_td = ("Assigned → QA Duration", "mean"),
        Avg_In_Progress_td    = ("In Progress Duration",   "mean"),
    )
    .reset_index()
)


rev_t = (
    df_avg
    .groupby(["Team", "Assignee"])
    .agg(Ticket_Count_rev=("Ticket Key", "count"))
    .reset_index()
)


rev_complexity_counts = (
    df_avg
    .groupby(["Assignee", "Request Complexity"])
    .size()
    .unstack(fill_value=0)
)
for lvl in range(1, 6):
    if lvl not in rev_complexity_counts.columns:
        rev_complexity_counts[lvl] = 0
rev_complexity_counts = (
    rev_complexity_counts
    .rename(columns=lambda x: f"CMPXrc {x}")
    .reset_index()
)


rev_weight_per_assignee = (
    df_avg
    .groupby("Assignee")["Weight"]
    .sum()
    .reset_index()
    .rename(columns={"Weight": "Coef_Sum_rev"})
)


rev_merged = pd.merge(rev_t, rev_complexity_counts, on="Assignee", how="left")
rev_final_summary = pd.merge(rev_merged, rev_weight_per_assignee, on="Assignee", how="left")


rev_team_totals = (
    rev_final_summary
    .groupby("Team")["Ticket_Count_rev"]
    .sum()
    .reset_index()
    .rename(columns={"Ticket_Count_rev": "Team_Total_Tickets_rev"})
)
rev_team_totals_complex = (
    rev_final_summary
    .groupby("Team")["Coef_Sum_rev"]
    .sum()
    .reset_index()
    .rename(columns={"Coef_Sum_rev": "Team_Total_Complex_rev"})
)

rev_final_summary = pd.merge(rev_final_summary, rev_team_totals, on="Team", how="left")
rev_final_summary = pd.merge(rev_final_summary, rev_team_totals_complex, on="Team", how="left")

rev_final_summary["Workload_rev"] = (
    (rev_final_summary["Coef_Sum_rev"] / rev_final_summary["Team_Total_Complex_rev"]) * 100
).round(2).astype(str) + " %"


avg_group["Avg_Assigned_to_QA"] = avg_group["Avg_Assigned_to_QA_td"].apply(
    lambda td: format_td(td) if pd.notna(td) else "00:00:00"
)
avg_group["Avg_In_Progress"] = avg_group["Avg_In_Progress_td"].apply(
    lambda td: format_td(td) if pd.notna(td) else "00:00:00"
)


avg_group = avg_group.drop(columns=["Avg_Assigned_to_QA_td", "Avg_In_Progress_td"])


combined = pd.merge(
    live_summary,
    rev_final_summary,
    on=["Team", "Assignee"],
    how="left"
)


final_summary = pd.merge(
    combined,
    avg_group,
    on=["Team", "Assignee"],
    how="left"
)


final_summary[["Avg_Assigned_to_QA", "Avg_In_Progress"]] = (
    final_summary[["Avg_Assigned_to_QA", "Avg_In_Progress"]]
    .fillna("00:00:00")
)


final_summary["Ticket_Count_rev"] = final_summary["Ticket_Count_rev"].fillna(0).astype(int)
final_summary["Team_Total_Tickets_rev"] = final_summary["Team_Total_Tickets_rev"].fillna(0).astype(int)
final_summary["Team_Total_Complex_rev"] = final_summary["Team_Total_Complex_rev"].fillna(0)

final_summary = final_summary.sort_values(by=["Team", "Assignee"])
final_summary = final_summary.rename(columns={"Coef_Sum_rev": "CS30rc", "Team_Total_Tickets_rev": "TTT30rc", "Team_Total_Complex_rev": "TTC30rc", "Ticket_Count_rev": "TC30rc", "Workload_rev": "Workload30rc"})

print("      Triple Whale  (data for the last 30 days)\n")
print("LIVE\n")
ASSIGNEE_WIDTH = 19
for team in final_summary["Team"].unique():
    print(f"{team}")
    team_df = final_summary[final_summary["Team"] == team].copy()

    team_df["Assignee"] = team_df["Assignee"].apply(
        lambda x: f"           {x:<{ASSIGNEE_WIDTH}}"
    )
    header_aligned = f"   {'Assignee':<{ASSIGNEE_WIDTH}}"
    team_df = team_df.rename(columns={"Assignee": header_aligned})
    display_cols = [
        header_aligned,
        "Ticket_Count",
        "Team_Total_Tickets",
        "Team_Total_Complex",
        "Assigned_to_QA",
        "In_Progress",
        "CMPX 1",
        "CMPX 2",
        "CMPX 3",
        "CMPX 4",
        "CMPX 5",
        "Coef_Sum",
        "Workload",
        "TC30rc",
        "TTT30rc",
        "TTC30rc",
        "Avg_Assigned_to_QA",
        "Avg_In_Progress",
        "CMPXrc 1",
        "CMPXrc 2",
        "CMPXrc 3",
        "CMPXrc 4",
        "CMPXrc 5",
        "CS30rc",
        "Workload30rc"

    ]

    print(team_df[display_cols].to_string(index=False))
