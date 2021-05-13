import re
pattern = re.compile(r'[^a-zA-Z0-9]+')
def camelcase(s):
    return pattern.sub('',s.title())
