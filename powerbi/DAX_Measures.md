# Power BI DAX Measures

Create a dedicated measure table named `Measures`.

```DAX
Total Revenue =
CALCULATE(
    SUM('Fact Orders'[total_amount]),
    'Fact Orders'[order_status] IN {"Completed", "Shipped"}
)

Gross Revenue =
SUMX(
    'Fact Order Items',
    'Fact Order Items'[quantity] * 'Fact Order Items'[price_per_unit]
)

Discount Amount =
SUMX(
    'Fact Order Items',
    'Fact Order Items'[quantity] * 'Fact Order Items'[price_per_unit] * 'Fact Order Items'[discount]
)

Net Line Revenue =
SUMX(
    'Fact Order Items',
    'Fact Order Items'[quantity] * 'Fact Order Items'[price_per_unit] * (1 - 'Fact Order Items'[discount])
)

Gross Profit =
SUMX(
    'Fact Sales Lines',
    'Fact Sales Lines'[gross_profit]
)

Profit Margin % =
DIVIDE([Gross Profit], [Total Revenue])

Total Orders =
CALCULATE(
    DISTINCTCOUNT('Fact Orders'[order_id]),
    'Fact Orders'[order_status] IN {"Completed", "Shipped"}
)

Total Customers =
DISTINCTCOUNT('Dim Customers'[customer_id])

Purchasing Customers =
CALCULATE(
    DISTINCTCOUNT('Fact Orders'[customer_id]),
    'Fact Orders'[order_status] IN {"Completed", "Shipped"}
)

Average Order Value =
DIVIDE([Total Revenue], [Total Orders])

Returned Orders =
DISTINCTCOUNT('Fact Returns'[order_id])

Return Rate % =
DIVIDE([Returned Orders], DISTINCTCOUNT('Fact Orders'[order_id]))

Repeat Customers =
COUNTROWS(
    FILTER(
        VALUES('Fact Orders'[customer_id]),
        CALCULATE(
            DISTINCTCOUNT('Fact Orders'[order_id]),
            'Fact Orders'[order_status] IN {"Completed", "Shipped"}
        ) > 1
    )
)

Repeat Customer Rate % =
DIVIDE([Repeat Customers], [Purchasing Customers])

Revenue Previous Month =
CALCULATE(
    [Total Revenue],
    DATEADD('Dim Calendar'[date], -1, MONTH)
)

MoM Revenue Growth % =
DIVIDE([Total Revenue] - [Revenue Previous Month], [Revenue Previous Month])

Revenue Previous Year =
CALCULATE(
    [Total Revenue],
    DATEADD('Dim Calendar'[date], -1, YEAR)
)

YoY Revenue Growth % =
DIVIDE([Total Revenue] - [Revenue Previous Year], [Revenue Previous Year])

Running Revenue =
CALCULATE(
    [Total Revenue],
    FILTER(
        ALLSELECTED('Dim Calendar'[date]),
        'Dim Calendar'[date] <= MAX('Dim Calendar'[date])
    )
)

At Risk Customers =
CALCULATE(
    DISTINCTCOUNT('RFM Segments'[customer_id]),
    'RFM Segments'[churn_status] IN {"At Risk", "Lost"}
)

At Risk Revenue =
CALCULATE(
    SUM('RFM Segments'[monetary]),
    'RFM Segments'[churn_status] IN {"At Risk", "Lost"}
)

Customer Revenue Rank =
RANKX(
    ALLSELECTED('Dim Customers'[customer_id]),
    [Total Revenue],
    ,
    DESC,
    Dense
)

Product Revenue Rank =
RANKX(
    ALLSELECTED('Dim Products'[product_id]),
    [Net Line Revenue],
    ,
    DESC,
    Dense
)
```

## Measures Using Fact Sales Lines

If you use `Fact Sales Lines` as the primary visual fact table:

```DAX
Sales Line Revenue =
CALCULATE(
    SUM('Fact Sales Lines'[net_line_amount]),
    'Fact Sales Lines'[order_status] IN {"Completed", "Shipped"}
)

Sales Line Units =
CALCULATE(
    SUM('Fact Sales Lines'[quantity]),
    'Fact Sales Lines'[order_status] IN {"Completed", "Shipped"}
)

Sales Line Discount =
CALCULATE(
    SUM('Fact Sales Lines'[discount_amount]),
    'Fact Sales Lines'[order_status] IN {"Completed", "Shipped"}
)
```

