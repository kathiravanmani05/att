import scrapy
from scrapy.http import Request
import pandas as pd

class TaxiSpider(scrapy.Spider):
    name = "taxi2"
    allowed_domains = ["airportstaxitransfers.com"]
    start_urls = ["https://airportstaxitransfers.com"]

    def parse(self, response):
        github_excel_url = 'https://github.com/kathiravanmani05/att/raw/main/input.xlsx'
        df = pd.read_excel(github_excel_url)
        #df = pd.read_excel('input.xlsx')
        for i in df.index[0:6000]:
            start = df.loc[i]['start']
            end = df.loc[i]['end']
            OriginCode = df.loc[i]['OriginCode']
            DestinationCode = df.loc[i]['DestinationCode']
            Route_start = df.loc[i]['Route start']
            Route_dest = df.loc[i]['Route dest']
            passenger_count = 1
            start_date = "23%2F07%2F2024"
            end_date = "23%2F07%2F2024"
            start_time = "10%3A00"
            end_time = "13%3A00"

            formatted_url = f"https://airportstaxitransfers.com/transportation/taxibookings/Transfer-from-{start}-to-{end}?loc1_name={start}&loc2_name={end}&pax1={passenger_count}&date1={start_date}&date2={end_date}&loc1={OriginCode}&loc2={DestinationCode}&single=1&time1={start_time}&time2={end_time}&quote=1"
            headers = {
                'Accept': 'application/json, text/javascript, */*; q=0.01',
                'Accept-Language': 'en-US,en;q=0.9',
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                #'Cookie': 'csrf_token=3788f77d-e745-4c05-b0cb-657899dbb8d3; _gcl_au=1.1.193510060.1714028033; _ga=GA1.1.299613019.1714028038; PHPSESSID=f69cutvgbj4d2k2lmksn27n0hs; _uetsid=29afbfd0046611efb023716b0536847a; _uetvid=153e467002d811ef86f989a78f65c50a; _ga_72Q0YQY7Y4=GS1.1.1714205754.5.0.1714205754.60.0.4790922; origin_new=undefined',
                'Pragma': 'no-cache',
                'Referer': 'https://airportstaxitransfers.com/',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-origin',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
                'X-Requested-With': 'XMLHttpRequest',
                'sec-ch-ua': '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"'
            }

            yield Request(formatted_url, callback=self.ids , headers=headers, meta={'url': formatted_url, 'start': start, 'end': end, 'Route_start': Route_start, 'Route_dest': Route_dest})

    def ids(self, response):
        Route_start = response.meta['Route_start']
        Route_dest = response.meta['Route_dest']
        link = response.meta['url']
        details = response.xpath('//*[@class="vehicle_select selection-box__tile"]')
        tans_details = response.xpath('//*[@class="res__headline text-center mb-30"]/text()').extract_first()
        try:
            tras_from = tans_details.split('from ')[1].split(' to ')[0]
            trans_to = tans_details.split('from ')[1].split(' to ')[1]
            search_from = response.xpath('//*[contains(text(),"From ")]/following::strong[1]/text()').extract_first()
            search_to = response.xpath('//*[contains(text(),"To ")]/following::strong[1]/text()').extract_first()
        except IndexError:
            tras_from = None
            trans_to = None
            
        x_passenger_prices = {i: [] for i in range(1, 17)}
        for detail in details:
            name = detail.xpath('.//*[@class="vehicle--name"]/text()').extract_first()
            passenger = detail.xpath('.//*[contains(text(),"passengers")]/span/text()').extract_first().strip()
            try:
                passenger = int(passenger)
                if passenger <= 16:
                    price = detail.xpath('.//*[@class="total-price change-price text-right"]/text()').extract_first()
                    if price:
                        price = price.replace('EUR ', '')
                        x_passenger_prices[passenger].append(price)
            except (ValueError, TypeError):
                pass
        
        lowest_prices = {}
        for passengers, prices in x_passenger_prices.items():
            if prices:
                lowest_prices[passengers] = prices[0]
            else:
                lowest_prices[passengers] = None
            
        pax_prices = {f'{i}pax': lowest_prices.get(i) for i in range(1, 17)}

        yield {
            'url': link,
            'from': response.meta['start'],
            'tras_from': tras_from,
            'search_from': search_from,
            'to': response.meta['end'],
            'trans_to': trans_to,
            'search_to': search_to,
            'Route_start': Route_start,
            'Route_dest': Route_dest,
            **pax_prices
        }
