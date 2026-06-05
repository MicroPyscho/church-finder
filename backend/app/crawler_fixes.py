# Run this once to patch the crawler with correct URLs and selectors
# Then delete this file

import re

with open('/app/app/crawler.py', 'r') as f:
    code = f.read()

# Fix 1: Allsop URLs
code = code.replace(
    '"https://www.allsop.co.uk/auctions/residential/"',
    '"https://www.allsop.co.uk/auctions/residential-auctions/"'
)
code = code.replace(
    '"https://www.allsop.co.uk/auctions/commercial/"',
    '"https://www.allsop.co.uk/auctions/commercial-auctions/"'
)

with open('/app/app/crawler.py', 'w') as f:
    f.write(code)

print('Allsop URLs fixed')
