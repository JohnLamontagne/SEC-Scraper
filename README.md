# SECScraper
Straight-forward automated scraping program to gather corporate filings from the Securities and Exchange Commission

# Requirements
- Python 3.6

# Dependencies
- [pdfkit](https://pypi.org/project/pdfkit/)
- [BeautifulSoup](https://pypi.org/project/beautifulsoup4/)

# Installation
**Git:**
```
git clone https://github.com/JohnLamontagne/SEC-Scraper.git
pip3 install -r requirements.txt
```

# Usage
```
python main.py -t "STOCK TICKER" 
```

# Optional Paramaters
- ```--directory value``` or ```-d value``` : Directory in which to output files (program will create a subdirectory named after the company ticker to which to dump files)
- ```--exclude value``` or ```-e value``` : Filing types to be excluded (e.g., "S-4"), seperated by commas if multiple.
- ```--include value``` or ```-i value``` : Filing types to be explicitly included. Utilizing this paramater will result in any form not specified being ignored for download.
- ```--enddate date``` : Furthest date from which to pull filings (furthest from the present)
- ```--startdate date``` : Soonest date from which to pull filings (closest to the present)
