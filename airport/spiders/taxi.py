import scrapy
import pandas as pd
import requests
import json
import os.path

class TaxiSpider(scrapy.Spider):
    name = "taxi"
    allowed_domains = ["airportstaxitransfers.com"]
    start_urls = ["https://airportstaxitransfers.com"]
    
    def __init__(self):
        super().__init__()
        self.conversion_rates = {}  # Dictionary to store conversion rates
    
    def load_conversion_rates(self):
        if os.path.exists("conversion_rates.json"):
            with open("conversion_rates.json", "r") as file:
                self.conversion_rates = json.load(file)
        else:
            self.update_conversion_rates()
    
    def save_conversion_rates(self):
        with open("conversion_rates.json", "w") as file:
            json.dump(self.conversion_rates, file)
    
    def update_conversion_rates(self):
        currencies = ['USD', 'EUR', 'GBP', 'JPY']  # Add more currencies as needed
        for currency in currencies:
            self.conversion_rates[currency] = self.fetch_conversion_rate(currency)
        self.save_conversion_rates()
    
    def fetch_conversion_rate(self, currency):
        url = f"https://www.xe.com/api/protected/statistics/?from={currency}&to=EUR"
        headers = {
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Pragma': 'no-cache',
            'Referer': f'https://www.xe.com/currencyconverter/convert/?Amount=1&From={currency}&To=EUR',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'authorization': 'Basic bG9kZXN0YXI6cHVnc25heA==',
            'sec-ch-ua': '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"'
        }
        response = requests.get(url, headers=headers)
        data = json.loads(response.text)
        conversion_rate = data["last1Days"]['average']
        return conversion_rate
    
    def convert_to_euro(self, currency, amount):
        if not self.conversion_rates:
            self.load_conversion_rates()
        if currency not in self.conversion_rates:
            self.update_conversion_rates()  # Fetch new rate if not available
        conversion_rate = self.conversion_rates.get(currency, 1)  # Default to 1 if rate not found
        converted_amount = amount * conversion_rate
        return round(converted_amount, 2)
    
    def parse(self, response):
        df = pd.read_excel('input.xlsx')
        for i in df.index[0:10]:
            start = df.loc[i]['start']
            end = df.loc[i]['end']
            OriginCode = df.loc[i]['OriginCode']
            DestinationCode = df.loc[i]['DestinationCode']
            start_date = "07%2F05%2F2024"
            end_date = "02%2F05%2F2024"
            start_time = "10%3A00"
            end_time = "13%3A00"
            Route_start = df.loc[i]['Route start']
            Route_dest = df.loc[i]['Route dest']
            for passenger_count in range(1, 17):
                formatted_url = f"https://airportstaxitransfers.com/transportation/taxibookings/Transfer-from-{start}-to-{end}?loc1_name={start}&loc2_name={end}&pax1={passenger_count}&date1={start_date}&date2={end_date}&loc1={OriginCode}&loc2={DestinationCode}&single=1&time1={start_time}&time2={end_time}&quote=1"
                headers = {
                    'Accept': 'application/json, text/javascript, */*; q=0.01',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Cache-Control': 'no-cache',
                    'Connection': 'keep-alive',
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
                yield scrapy.Request(formatted_url, callback=self.ids, headers=headers, meta={'url': formatted_url, 'start': start, 'end': end, 'passenger_count': passenger_count,'Route_start':Route_start,'Route_dest':Route_dest})
                
    def ids(self, response):
        link = response.meta['url']
        passenger_count = response.meta['passenger_count']
        Route_start = response.meta['Route_start']
        Route_dest =response.meta['Route_dest']
        details = response.xpath('//*[@class="vehicle_select selection-box__tile"]')
        tans_details = response.xpath('//*[@class="res__headline text-center mb-30"]/text()').extract_first()
        try:
            tras_from = tans_details.split('from ')[1].split(' to ')[0]
            trans_to = tans_details.split('from ')[1].split(' to ')[1]
            search_from = response.xpath('//*[contains(text(),"From ")]/following::strong[1]/text()').extract_first()
            search_to = response.xpath('//*[contains(text(),"To ")]/following::strong[1]/text()').extract_first()
        except:
            tras_from = None
            trans_to = None
        x_paxs = {i: [] for i in range(1, 17)}
        for detail in details:
            name = detail.xpath('.//*[@class="vehicle--name"]/text()').extract_first()
            passanger = detail.xpath('.//*[contains(text(),"passengers")]/span/text()').extract_first().strip()
            passanger = int(passanger)
            if passanger > 16:
                continue
            price = detail.xpath('.//*[@class="total-price change-price text-right"]/text()').extract_first()
            if price:
                price = price.split()
                currency = price[0]
                amount = float(price[1].replace(',', ''))
                x_paxs[passanger].append((currency, amount))
        lowest_values = {}
        for passengers, prices in x_paxs.items():
            if prices:
                lowest_values[passengers] = prices[0]
            else:
                lowest_values[passengers] = None
        converted_prices = {}
        for passengers, price in lowest_values.items():
            if price:
                currency, amount = price
                converted_price = self.convert_to_euro(currency, amount)
                converted_prices[f'{passengers}pax'] = converted_price
        yield {
            'url': link,
            'Route_start':Route_start,
            'Route_dest' :Route_dest,
            'from': response.meta['start'],
            'tras_from': tras_from,
            'search_from': search_from,
            'to': response.meta['end'],
            'trans_to': trans_to,
            'search_to': search_to,
            f'{passenger_count}pax': converted_prices.get(f'{passenger_count}pax', None)
        }
