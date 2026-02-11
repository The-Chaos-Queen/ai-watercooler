
import os
import re
from bs4 import BeautifulSoup
import markdownify

def extract_gemini_chat(file_path):
    print(f"Reading file: {file_path}")
    with open(file_path, 'r', encoding='utf-8') as f:
        html_content = f.read()

    print("Parsing HTML with lxml...")
    # Use lxml for speed
    soup = BeautifulSoup(html_content, 'lxml')

    print("Cleaning up DOM (removing script, style, svg)...")
    # Remove heavy tags
    for tag in soup(['script', 'style', 'svg', 'iframe', 'noscript', 'meta', 'link']):
        tag.decompose()

    print("Finding message containers...")
    
    # Use regex for class search which is faster than python function
    container_pattern = re.compile(r'query-container|response-container')
    all_containers = soup.find_all(class_=container_pattern)
    
    print(f"Found {len(all_containers)} potential containers.")
    
    unique_containers = []
    
    # Filter nested containers.
    # Logic: Keep only top-level ones.
    # To speed this up, we can assume document order is preserved.
    # If A contains B, A comes before B usually in finding list?
    # No, find_all returns in document order.
    # If A contains B, A starts before B.
    
    # Efficient filtering:
    if all_containers:
        # Sort by depth or just check ancestors?
        # Checking ancestors for each is safe.
        # Speed optimization: Cache parents?
        # Let's stick to the O(N^2) for now, assuming N is small (<1000).
        # If N is large, this will be slow.
        pass

    # Actually, let's try a smarter filter.
    # If we iterate and check if current is contained in any *already accepted* container?
    # No, because A (accept) -> B (reject).
    # But what if B (reject) is inside A?
    # If we process in order, we accept A. Then we see B. Is B inside A? Yes -> Reject B.
    # This assumes strict nesting.
    # What if A and C are siblings? B inside A.
    # Accept A. Process B. B is inside A -> Reject B. Process C. C is not inside A -> Accept C.
    

    accepted = []
    for container in all_containers:
        is_inside_accepted = False
        # Check if any parent is already in accepted list
        # This is fast because depth is small
        for parent in container.parents:
            if parent in accepted:
                is_inside_accepted = True
                break
        
        if not is_inside_accepted:
             accepted.append(container)
             
    unique_containers = accepted
             
    unique_containers = accepted
    print(f"Filtered to {len(unique_containers)} unique top-level containers.")

    messages = []
    
    for container in unique_containers:
        classes = ' '.join(container.get('class', []))
        role = "Unknown"
        if 'query-container' in classes:
            role = "User"
        elif 'response-container' in classes:
            role = "Gemini"
        
        content_node = container
        if role == "Gemini":
            md_node = container.find(class_='markdown')
            if md_node:
                content_node = md_node
                
        # Handle code blocks better? markdownify is decent.
        text = markdownify.markdownify(str(content_node), heading_style="ATX")
        
        # Clean up
        text = re.sub(r'\n{3,}', '\n\n', text).strip()
        
        if text:
            messages.append({'role': role, 'content': text})

    output = "# Gemini Chat Export\n\n"
    for msg in messages:
        output += f"## {msg['role']}\n\n{msg['content']}\n\n---\n\n"
        
    return output

if __name__ == "__main__":
    input_file = r"C:\Users\cerub\OneDrive\Dokumente\LLM\my gemini.html"
    output_file = r"C:\Users\cerub\OneDrive\Dokumente\LLM\my_gemini_export.md"
    
    try:
        md = extract_gemini_chat(input_file)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(md)
        print("Done.")
    except Exception as e:
        print(f"Error: {e}")
