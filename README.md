# Twitter-Scraper-Script
A Twitter Scraper Script 

Example Input for scraper:

python scraper --username=@realDonaldTrump

python scraper -u realDonaldTrump

python scraper --user=@xxx --password=xxx --query="Jan 2020 (from:BurgerKing) until:2020-01-31 since:2020-01-01" -t 100

python scraper -t 3200 --user=@xxx --password=xxx -u realDonaldTrump

python scraper --user=@xxx --password=xxx --query="(from:BurgerKing) until:2020-01-31 since:2020-01-01 -filter:replies" -t 300

python scraper --user=@xxx --password=xxx --query="(from:Lakers) until:2020-01-31 since:2020-01-01 -filter:replies" -t 300

Example Input for scraper runner:

Enter the Twitter username (without @): BurgerKing
Enter the start date (YYYY-MM-DD): 2020-01-01
Enter the end date (YYYY-MM-DD): 2020-02-31

