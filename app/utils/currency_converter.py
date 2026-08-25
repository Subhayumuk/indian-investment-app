from typing import Dict, Optional

class CurrencyConverter:
    def __init__(self):
        self.fx_rates_to_inr = {
            "USD": 83.5, "EUR": 90.2, "GBP": 105.8, "AUD": 54.3,
            "SGD": 62.1, "CAD": 61.8, "AED": 22.7, "DKK": 12.1,
            "JPY": 0.56, "CHF": 93.4, "NZD": 50.2, "SEK": 7.9,
            "NOK": 7.8, "HKD": 10.7, "MYR": 17.8,
        }
        self.country_currency = {
            "usa": "USD", "uk": "GBP", "germany": "EUR", "france": "EUR",
            "denmark": "DKK", "australia": "AUD", "singapore": "SGD",
            "canada": "CAD", "uae": "AED", "japan": "JPY", "switzerland": "CHF",
            "sweden": "SEK", "norway": "NOK", "hong kong": "HKD", "malaysia": "MYR",
        }

    def get_currency_for_country(self, country: str) -> str:
        return self.country_currency.get(country.lower(), "USD")

    def to_inr(self, amount: float, from_currency: str) -> float:
        rate = self.fx_rates_to_inr.get(from_currency.upper(), 83.5)
        return round(amount * rate, 2)

    def from_inr(self, amount_inr: float, to_currency: str) -> float:
        rate = self.fx_rates_to_inr.get(to_currency.upper(), 83.5)
        if rate == 0:
            return 0
        return round(amount_inr / rate, 2)

    def convert(self, amount: float, from_currency: str, to_currency: str) -> float:
        if from_currency.upper() == to_currency.upper():
            return amount
        amount_inr = self.to_inr(amount, from_currency)
        return self.from_inr(amount_inr, to_currency)

    def get_rate(self, currency: str) -> float:
        return self.fx_rates_to_inr.get(currency.upper(), 83.5)

    def format_amount(self, amount: float, currency: str) -> str:
        symbols = {"USD": "$", "EUR": "€", "GBP": "£", "AUD": "A$", "SGD": "S$", "CAD": "C$", "AED": "AED ", "DKK": "kr ", "INR": "₹"}
        symbol = symbols.get(currency.upper(), f"{currency} ")
        if amount >= 10000000:
            return f"{symbol}{amount/10000000:.2f} Cr"
        elif amount >= 100000:
            return f"{symbol}{amount/100000:.2f} L"
        else:
            return f"{symbol}{amount:,.0f}"
