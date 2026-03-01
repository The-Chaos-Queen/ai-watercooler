import argparse
import os

try:
    import tree_sitter_python
    from tree_sitter import Language, Parser
except ImportError:
    print("Error: tree_sitter or tree_sitter_python is not installed. Please run 'pip install tree-sitter tree-sitter-python'")
    exit(1)

def map_python_file(filepath):
    try:
        PY_LANGUAGE = Language(tree_sitter_python.language())
        parser = Parser()
        parser.set_language(PY_LANGUAGE)

        with open(filepath, "rb") as f:
            code_bytes = f.read()
        
        tree = parser.parse(code_bytes)
        
        # Super simple query avoiding complex docstring parsing that fails on version changes
        query = PY_LANGUAGE.query("""
            (class_definition name: (identifier) @class_name)
            (function_definition name: (identifier) @func_name)
        """)
        
        captures = query.captures(tree.root_node)
        
        print(f"--- Map of {filepath} ---")
        
        # Different versions of tree_sitter return dicts vs list of tuples.
        if isinstance(captures, dict):
            for name, nodes in captures.items():
                for node in nodes:
                    print(f"[{name.upper()}] {node.text.decode('utf-8')} (Line {node.start_point[0]+1})")
        else:
            for node, name in captures:
                print(f"[{name.upper()}] {node.text.decode('utf-8')} (Line {node.start_point[0]+1})")
                
    except Exception as e:
        print(f"Failed to tree-sit {filepath}: {e}")

def main():
    parser = argparse.ArgumentParser(description="Map a Python file using tree-sitter.")
    parser.add_argument("filepath", help="Path to the .py file")
    args = parser.parse_args()
    
    input_path = os.path.abspath(args.filepath)
    if not os.path.exists(input_path):
        print(f"Error: {input_path} not found.")
        return
        
    map_python_file(input_path)

if __name__ == "__main__":
    main()
