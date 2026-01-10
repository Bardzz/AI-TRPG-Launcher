import re

def markdown_to_text(md_text: str) -> str:
    text = re.sub(r'^(#+)\s+', '', md_text, flags=re.M)
    text = re.sub(r'\*\*?([^*]+)\*\*?', r'\1', text)
    text = re.sub(r'!\[([^\]]*)\]\([^)]+\)', r'\1', text)
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    text = re.sub(r'^>\s+', '', text, flags=re.M)
    text = re.sub(r'`{3}[\s\S]*?`{3}', '', text)
    text = re.sub(r'`([^`]+)`', r'\1', text)
    text = re.sub(r'^(-|\*)\s+', '', text, flags=re.M)
    text = re.sub(r'^---+$', '', text, flags=re.M)
    return text.strip()
