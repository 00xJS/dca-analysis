# Project Title: Modeling Dollar Cost Averaging for Bitcoin Investments

## Project Background
Dollar Cost Averaging (DCA) is an investment strategy where an investor divides up the total amount to be invested across periodic purchases of a target asset to reduce the impact of volatility on the overall purchase. The goal of this project was to demonstrate how DCA could be applied to Bitcoin investments by using historical price data. This approach would allow individuals to understand the potential benefits and returns of systematically investing in Bitcoin, similar to how one might contribute to a 401(k) or retirement fund.

The initial challenge was finding and preparing suitable data. Historical Bitcoin price data was [sourced from Kaggle](https://www.kaggle.com/datasets/mczielinski/bitcoin-historical-data) which provided minute-by-minute price details but in Unix timestamp format. Converting this to daily data was necessary to simulate weekly or bi-weekly investment strategies which are more realistic for regular investors.

## Project Breakdown
Data Acquisition and Preparation:
- Source: Kaggle was used to find a dataset with Bitcoin price history from minute to minute.
- Conversion: The data, originally in Unix seconds, was converted into readable dates. 
- Aggregation: The minute-by-minute data was aggregated into daily prices to simplify analysis and simulate realistic investment intervals.

Data Conversion to Daily:
- A function convert_to_daily was created to aggregate minute data into daily averages for Open, High, Low, Close prices, and sum for Volume. This step was crucial as it allowed for the simulation of regular investment periods.
  
DCA Simulation:
 - *Function Development*: A Python function calculate_dca was implemented to simulate buying Bitcoin at regular intervals. Parameters included:
   - *investment_amount*: The dollar amount to invest each time ($100 in our base scenario).
   - *frequency_days*: The interval between investments (set to 14 days for bi-weekly investment, mirroring a typical payday schedule).
   - *start_date and end_date*: The investment period was from January 27, 2020, to January 27, 2025 using 1, 3 & 5 year timelines.
   
Simulation: 
 - The function tracked the total invested, total Bitcoin purchased, and calculated the return on investment based on the final Bitcoin price in the dataset.

Analysis and Reporting:
 - The results of the DCA strategy were analyzed to calculate key performance indicators like total invested, total Bitcoin acquired, final value, and ROI.
The data was exported to CSV for further visualization or analysis.

## Conclusion
This project successfully illustrated how Dollar Cost Averaging could be applied to Bitcoin investments over a long-term horizon. By converting minute data to daily data and simulating investments every two weeks, we've shown that DCA can mitigate the impact of price volatility. 

- The results suggest that:
  - Even with Bitcoin's high volatility, a regular investment strategy like DCA can lead to significant gains over time, especially if one considers this as part of a retirement or long-term savings plan.
  - The ROI calculated from this model underscores the potential of Bitcoin as an investment vehicle when approached systematically.

This model can be adapted for different investment amounts, frequencies, or even applied to other cryptocurrencies or investment vehicles. It serves as a practical example for anyone interested in understanding or implementing DCA strategies in the cryptocurrency market.
