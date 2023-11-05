# Author: John LaMontagne, Associate Researcher.
# jlamontagne@ufcw.org
# Date: 11/19/2018

import urllib.request
import requests
import json
import os
from bs4 import BeautifulSoup
import pdfkit
import re
import shutil
from argparse import ArgumentParser
from datetime import datetime
from dateutil.parser import *


def remove_disallowed_chars(filename):
    return re.sub('[^\w_.)( -]', '', filename)

class SECNinja:

    hdr = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11',
           'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
           'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
           'Accept-Encoding': 'none',
           'Accept-Language': 'en-US,en;q=0.8',
           'Connection': 'keep-alive'}

    def __init__(self, cik, working_dir, excluded_forms, included_forms, enddate, startdate):
        self.cik = cik
        self.working_dir = working_dir
        self.excluded_forms = excluded_forms
        self.included_forms = included_forms

        if enddate is not None:
            self.enddate = parse(enddate, default=datetime(2019, 1, 1))
        else:
            self.enddate = None

        if startdate is not None:
            self.startdate = parse(startdate, default=datetime(2001, 1, 1))
        else:
            self.startdate = None

        self.offset = 0
        self.sec_base_url = "https://www.sec.gov"
        self.init_dirs()
        self.pdfconfig = pdfkit.configuration(wkhtmltopdf="C:/Program Files/wkhtmltopdf/bin/wkhtmltopdf.exe")

    def init_dirs(self):
        self.root_path = os.path.join(self.working_dir, self.cik, "SEC")
        self.exhibits_path = os.path.join(self.root_path, "Exhibits")

        if not os.path.exists(self.root_path):
            try:
                os.makedirs(self.root_path)
            except OSError as exception:
                if exception.errno != errno.EEXIST:
                    raise

        if not os.path.exists(self.exhibits_path):
            try:
                os.makedirs(self.exhibits_path)
            except OSError as exception:
                if exception.errno != errno.EEXIST:
                    raise

    def save_doc(self, doc_type, doc_url, filing_date, parent = None):
        extension = os.path.splitext(doc_url)[1]

        if 'html' in extension or 'htm' in extension:
            # Save exhibits in their desginated folder.
            if ("EX" in doc_type):
                pdfkit.from_url(doc_url, os.path.join(self.exhibits_path, filing_date + ' Form ' + parent + ' ' + doc_type + '.pdf'), configuration=self.pdfconfig)
            else:
                pdfkit.from_url(doc_url, os.path.join(self.root_path, filing_date + ' Form ' + doc_type + '.pdf'), configuration=self.pdfconfig)
        elif 'pdf' in extension or 'txt' in extension or 'xml' in extension:
            req = requests.get(doc_url, headers=self.hdr)

            if ("EX" in doc_type):
                with open(os.path.join(self.exhibits_path, filing_date + ' Form ' + parent + ' ' + doc_type + extension), 'wb') as f:
                    f.write(req.content)
            else:
                with open(os.path.join(self.root_path, filing_date + ' Form ' + doc_type + extension), 'wb') as f:
                    f.write(req.content)

    def grab_filing_docs(self, url):
        req = requests.get(self.sec_base_url + url, headers=self.hdr)
        soup = BeautifulSoup(req.text, 'html.parser')

        filing_label = soup.find('div', text='Filing Date')

        if (filing_label is None):
            return

        filing_date = filing_label.find_next_sibling().text

        doc_section = soup.find('table', attrs={'summary': 'Document Format Files'})

        doc_rows = doc_section.findChildren('tr')

        # remove first element from the array (SEC is daft and uses row 1 as header rather than correctly defining it)
        doc_rows = doc_rows[1: ]

        parent = None

        for row in doc_rows:
            columns = row.findChildren('td')

            doc_type = columns[3].text
            doc_desc = columns[1].text
            doc_url = self.sec_base_url + columns[2].find('a')['href']

            # This should always be None the first time around, and the first document we parse
            # should always be the standard.... hopefully
            if (parent is None):
                parent = remove_disallowed_chars(doc_type)

            # ignore the garbage
            if (not doc_type or not doc_desc or 'GRAPHIC' in doc_type or 'submission text file' in doc_desc):
                continue

            print("Grabbing form " + doc_type + ": " + doc_url)
            self.save_doc(remove_disallowed_chars(doc_type), doc_url, filing_date, parent)

        print('---- END OF FILING ----')

    def build_base_url(self):
        return "https://www.sec.gov/cgi-bin/browse-edgar?CIK=" + self.cik + "&owner=include&action=getcompany&start=" + str(self.offset) + "&count=100"

    def grab_filings(self, url):
        req = requests.get(url, headers=self.hdr)
        soup = BeautifulSoup(req.text, 'html.parser')

        filing_table = soup.find('table', attrs={'class': 'tableFile2'})

        if (filing_table is None):
            return

        # grab all of the table rows excluding the first (for some reason the SEC uses the first row for column headers.... facepalm)
        filing_rows = filing_table.findChildren('tr')[1:]

        # We've reached the end of the rope... let's get out of here.
        if (len(filing_rows) <= 1 or filing_rows is None):
            return

        for row in filing_rows:
            columns = row.findChildren('td')
            filing_type = columns[0].text

            # if include-forms was specified, we will only be downloading docs specified explicitly
            if self.included_forms and not any(True for form in self.included_forms if form.strip() == filing_type.strip()):
                print("Ignoring {} as it is not an explicitly included form.".format(filing_type))
                continue

            # ignore excluded forms.
            elif any(True for form in self.excluded_forms if form.strip() == filing_type.strip()):
                print("Ignoring {} as an excluded form.".format(filing_type))
                continue

            # ignore forms dated outside of our date-range.
            date = datetime.strptime(columns[3].text.strip(), "%Y-%m-%d")

            if self.startdate is not None and date > self.startdate:
                print("Filing was made after {}: ignoring...".format(self.startdate))
                continue

            if self.enddate is not None and date < self.enddate:
                print("Filing was made prior to {}: ignoring...".format(self.enddate))
                continue

            filing_link = columns[1].find('a', attrs={'id': 'documentsbutton'})['href']
            self.grab_filing_docs(filing_link)


        # Check to see whether there are more results...
        # Again, the SEC website is horribly designed, not even sure if by humans, so it seems the only way to do this is to check whether
        # there exists a button labeled 'Next 100' at the bottom of the page.
        self.offset = self.offset + 100
        self.grab_filings(self.build_base_url())

    def begin_scraping(self):
        # testing: will only grab 10-Ks
        docs = self.grab_filings(self.build_base_url())
        print('Finished scraping SEC filings!')


def main():
    parser = ArgumentParser()
    parser.add_argument('-t', '--ticker',
                        help='Stock ticker for the target company.')
    parser.add_argument('-d', '--directory', default='./',
                        help='Directory in which to output files.')
    parser.add_argument('-e', '--exclude', help='Filing types to be excluded (e.g., "S-4"), seperated by commas if multiple.', default='')
    parser.add_argument('-i', '--include', help='Filing types to be explicitly included. Utilizing this paramater will result in any form not specified being ignored for download.')
    parser.add_argument('--enddate', help='Furthest date from which to pull filings (furthest from the present)', default=None)
    parser.add_argument('--startdate', help='Soonest date from which to pull filings (closest to the present)', default=None)

    args = parser.parse_args()

    if not args.ticker:
        raise Exception('Ticker not specified!')

    if args.include:
        grabber = SECNinja(args.ticker, args.directory, [], args.include.split(','), args.enddate, args.startdate)
    else:
        if not args.exclude:
            grabber = SECNinja(args.ticker, args.directory, [], [], args.enddate, args.startdate)
        else:
            grabber = SECNinja(args.ticker, args.directory, args.exclude.split(','), [], args.enddate, args.startdate)

    grabber.begin_scraping()

main()
