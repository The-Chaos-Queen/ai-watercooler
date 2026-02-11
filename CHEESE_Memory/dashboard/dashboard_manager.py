import json
import argparse
import sys
import datetime
from pathlib import Path

# Configuration
DASHBOARD_DIR = Path("C:/Users/cerub/OneDrive/Dokumente/LLM/CHEESE_Memory/dashboard")
DATA_FILE = DASHBOARD_DIR / "dashboard_data.json"
MARKDOWN_FILE = DASHBOARD_DIR.parent / "00_DASHBOARD.md" # In CHEESE_Memory root
HTML_FILE = DASHBOARD_DIR / "dashboard_view.html"

def load_data():
    if not DATA_FILE.exists():
        print(f"Error: {DATA_FILE} not found.")
        sys.exit(1)
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def get_current_time():
    # Return current ISO time with timezone offset (Assuming User is Berlin/CET +01:00)
    # Using simple isoformat for now, better timezone support can be added if env has libraries
    return datetime.datetime.now().astimezone().isoformat()

def update_global_time(data):
    data['last_active_global'] = get_current_time()
    return data

def action_focus(project_id):
    data = load_data()
    data = update_global_time(data)
    
    # Validate ID
    valid_ids = [p['id'] for p in data['projects']]
    if project_id not in valid_ids:
        print(f"Error: Project ID '{project_id}' not found.")
        return

    data['active_focus_id'] = project_id
    
    # Move to top of priority stack if not there
    stack = data['priority_stack']
    # Remove if exists
    stack = [item for item in stack if item['id'] != project_id]
    # Add to top
    stack.insert(0, {'id': project_id, 'reason': 'User Focus Command'})
    data['priority_stack'] = stack

    # Update project status to Hot
    for p in data['projects']:
        if p['id'] == project_id:
            p['status'] = 'Hot'
            p['last_touched'] = get_current_time()
            p['interaction_count_today'] += 1
            p['interaction_count_total'] += 1

    save_data(data)
    print(f"Focus switched to: {project_id}")
    sync_views()

def action_note(project_id, text):
    data = load_data()
    data = update_global_time(data)
    
    found = False
    for p in data['projects']:
        if p['id'] == project_id:
            p['resume_context']['last_user_input'] = f"[Note] {text}"
            p['last_touched'] = get_current_time()
            found = True
            break
    
    if not found:
        print(f"Error: Project ID '{project_id}' not found.")
        return

    save_data(data)
    print(f"Note added to {project_id}")
    sync_views()

def action_update_time():
    data = load_data()
    data = update_global_time(data)
    # Also update the 'today' duration logic here (simplified for now)
    save_data(data)
    print("Time updated.")
    sync_views()

def generate_markdown(data):
    # Header
    md = f"# C.H.E.E.S.E. Orchestrator Dashboard\n\n"
    md += f"**System Time:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')} (Local)\n"
    md += f"**Last Update:** {data['last_active_global']}\n\n"

    # Find Active Project
    active_p = next((p for p in data['projects'] if p['id'] == data['active_focus_id']), None)
    
    if active_p:
        md += f"## 🔥 Active Focus: {active_p['name']}\n"
        md += f"> **Status:** {active_p['status']} | **Last Scene:** {active_p['resume_context']['last_scene']}\n"
        md += f"> **Unresolved:** {active_p['resume_context']['unresolved']}\n"
        md += f"> **Target Tone:** {active_p['resume_context']['tone_target']}\n\n"
        md += f"[Open Main File]({active_p['path']})\n\n"

    # Priority Stack
    md += "## ⚡ Priority Queue\n"
    md += "| Project | Status | Last Touch | Reason |\n"
    md += "|---|---|---|---|\n"
    
    # Create a map for quick lookup
    p_map = {p['id']: p for p in data['projects']}
    
    for item in data['priority_stack']:
        pid = item['id']
        if pid in p_map:
            p = p_map[pid]
            # Simple "Time Ago" logic could go here
            last_touch = p['last_touched'].split('T')[1][:5] # HH:MM extraction roughly
            md += f"| **{p['name']}** | {p['status']} | {last_touch} | {item['reason']} |\n"

    # The Freezer / All Projects
    md += "\n## 🧊 The Archive / Repository\n"
    for p in data['projects']:
        md += f"- **{p['name']}** ({p['status']}): [Link]({p['path']})\n"

    return md

def sync_views():
    data = load_data()
    
    # Markdown
    md_content = generate_markdown(data)
    with open(MARKDOWN_FILE, 'w', encoding='utf-8') as f:
        f.write(md_content)
    print(f"Updated {MARKDOWN_FILE}")

    # HTML (Placeholder for now, logic similar to MD)
    # create_html_view(data) 

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Manage C.H.E.E.S.E. Dashboard")
    parser.add_argument("--focus", help="Switch focus to project ID")
    parser.add_argument("--note", help="Add a note to a project")
    parser.add_argument("--id", help="Project ID for note")
    parser.add_argument("--update_time", action="store_true", help="Update global timestamp")
    parser.add_argument("--sync", action="store_true", help="Force sync views")

    args = parser.parse_args()

    if args.focus:
        action_focus(args.focus)
    elif args.note and args.id:
        action_note(args.id, args.note)
    elif args.update_time:
        action_update_time()
    elif args.sync:
        sync_views()
    else:
        # Default behavior: Update time
        action_update_time()
