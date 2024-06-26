import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
%matplotlib inline

# Import Statsmodels
from statsmodels.tsa.api import VAR
from statsmodels.tsa.stattools import adfuller
from statsmodels.tools.eval_measures import rmse, aic

#1. rgnp  : Real GNP.
#2. pgnp  : Potential real GNP.
#3. ulc   : Unit labor cost.
#4. gdfco : Fixed weight deflator for personal consumption expenditure excluding food and energy.
#5. gdf   : Fixed weight GNP deflator.
#6. gdfim : Fixed weight import deflator.
#7. gdfcf : Fixed weight deflator for food in personal consumption expenditure.
#8. gdfce : Fixed weight deflator for energy in personal consumption expenditure.

filepath = 'https://raw.githubusercontent.com/selva86/datasets/master/Raotbl6.csv'
df = pd.read_csv(filepath, parse_dates=['date'], index_col='date')
print(df.shape)  # (123, 8)
df.tail()

#plot the images

fig, axes = plt.subplots(nrows=4,ncols=2, dpi=120,figsize=(10,6))

for i, ax in enumerate(axes.flatten()):
    data = df[df.columns[i]]
    ax.plot(data, color = 'red', linewidth = 1)
    #decoration
    ax.set_title(df.columns[i])
    ax.xaxis.set_ticks_position('none')
    ax.yaxis.set_ticks_position('none')
    ax.spines['top'].set_alpha(0)
    ax.tick_params(labelsize=6)
    
plt.tight_layout();


# 6. Testing Causation using Granger’s Causality Test
# The basis behind Vector AutoRegression is that each of the time series in the system influences each other. That is, you can predict the series with past values of itself along with other series in the system.

# Using Granger’s Causality Test, it’s possible to test this relationship before even building the model.

# So what does Granger’s Causality really test?

# Granger’s causality tests the null hypothesis that the coefficients of past values in the regression equation is zero.

# In simpler terms, the past values of time series (X) do not cause the other series (Y). So, if the p-value obtained from the test is lesser than the significance level of 0.05, then, you can safely reject the null hypothesis.

# The below code implements the Granger’s Causality test for all possible combinations of the time series in a given dataframe and stores the p-values of each combination in the output matrix.

# Granger defined the causality relationship based on two principles:

#     1:The cause happens prior to its effect.
#     2:The cause has unique information about the future values of its effect.
# Given these two assumptions about causality, Granger proposed to test the following hypothesis for identification of a causal effect of X on Y:


from statsmodels.tsa.stattools import grangercausalitytests
maxlag=12
test = 'ssr_chi2test'


def grangers_causation_matrix(data, variables, test='ssr_chi2test', verbose=False):    
    """Check Granger Causality of all possible combinations of the Time series.
    The rows are the response variable, columns are predictors. The values in the table 
    are the P-Values. P-Values lesser than the significance level (0.05), implies 
    the Null Hypothesis that the coefficients of the corresponding past values is 
    zero, that is, the X does not cause Y can be rejected.

    data      : pandas dataframe containing the time series variables
    variables : list containing names of the time series variables.
    """
    df = pd.DataFrame(np.zeros((len(variables), len(variables))), columns=variables, index=variables)
    for c in df.columns:
        for r in df.index:
            test_result = grangercausalitytests(data[[r, c]], maxlag=maxlag, verbose=False)
            p_values = [round(test_result[i+1][0][test][1],4) for i in range(maxlag)]
            if verbose: print(f'Y = {r}, X = {c}, P Values = {p_values}')
            min_p_value = np.min(p_values)
            df.loc[r, c] = min_p_value
    df.columns = [var + '_x' for var in variables]
    df.index = [var + '_y' for var in variables]
    return df

grangers_causation_matrix(df, variables = df.columns) 


# So how to read the above output?

# The row are the Response (Y) and the columns are the predictor series (X). For example, if you take the value 0.0003 in (row 1, column 2), it refers to the p-value of pgnp_x causing rgnp_y. Whereas, the 0.000 in (row 2, column 1) refers to the p-value of rgnp_y causing pgnp_x.

# So, how to interpret the p-values?

# If a given p-value is < significance level (0.05), then, the corresponding X series (column) causes the Y (row).

# For example, P-Value of 0.0003 at (row 1, column 2) represents the p-value of the Grangers Causality test for pgnp_x causing rgnp_y, which is less that the significance level of 0.05.

# So, you can reject the null hypothesis and conclude pgnp_x causes rgnp_y.

# Looking at the P-Values in the above table, you can pretty much observe that all the variables (time series) in the system are interchangeably causing each other.

# This makes this system of multi time series a good candidate for using VAR models to forecast.

# Next, let’s do the Cointegration test

# Cointegration Test Cointegration test helps to establish the presence of a statistically significant connection between two or more time series.
# But, what does Cointegration mean?

# To understand that, you first need to know what is ‘order of integration’ (d).

# Order of integration(d) is nothing but the number of differencing required to make a non-stationary time series stationary.

# Now, when you have two or more time series, and there exists a linear combination of them that has an order of integration (d) less than that of the individual series, then the collection of series is said to be cointegrated.

# Ok?

# When two or more time series are cointegrated, it means they have a long run, statistically significant relationship.

# This is the basic premise on which Vector Autoregression(VAR) models is based on. So, it’s fairly common to implement the cointegration test before starting to build VAR models.

# Alright, So how to do this test?

# Soren Johanssen in his paper (1991) devised a procedure to implement the cointegration test.

# It is fairly straightforward to implement in python’s statsmodels, as you can see below.


from statsmodels.tsa.vector_ar.vecm import coint_johansen

def cointegration_test(df, alpha=0.05): 
    """Perform Johanson's Cointegration Test and Report Summary"""
    out = coint_johansen(df,-1,5)
    d = {'0.90':0, '0.95':1, '0.99':2}
    traces = out.lr1
    cvts = out.cvt[:, d[str(1-alpha)]]
    def adjust(val, length= 6): return str(val).ljust(length)

    # Summary
    print('Name   ::  Test Stat > C(95%)    =>   Signif  \n', '--'*20)
    for col, trace, cvt in zip(df.columns, traces, cvts):
        print(adjust(col), ':: ', adjust(round(trace,2), 9), ">", adjust(cvt, 8), ' =>  ' , trace > cvt)

cointegration_test(df)


# Split the Series into Training and Testing Data Splitting the dataset into training and test data.
# The VAR model will be fitted on df_train and then used to forecast the next 4 observations. These forecasts will be compared against the actuals present in test data.

# To do the comparisons, we will use multiple forecast accuracy metrics, as seen later in this article.

nobs = 4
df_train, df_test = df[0:-nobs], df[-nobs:]

# Check size
print(df_train.shape)  # (119, 8)
print(df_test.shape)  # (4, 8)

# 9. Check for Stationarity and Make the Time Series Stationary
# Since the VAR model requires the time series you want to forecast to be stationary, it is customary to check all the time series in the system for stationarity.

# Just to refresh, a stationary time series is one whose characteristics like mean and variance does not change over time.

# So, how to test for stationarity?

# There is a suite of tests called unit-root tests. The popular ones are:

# Augmented Dickey-Fuller Test (ADF Test)
# KPSS test
# Philip-Perron test
# Let’s use the ADF test for our purpose.

# By the way, if a series is found to be non-stationary, you make it stationary by differencing the series once and repeat the test again until it becomes stationary.

# Since, differencing reduces the length of the series by 1 and since all the time series has to be of the same length, you need to difference all the series in the system if you choose to difference at all.

# Got it?

# Let’s implement the ADF Test.

# First, we implement a nice function (adfuller_test()) that writes out the results of the ADF test for any given time series and implement this function on each series one-by-one



def adfuller_test(series, signif=0.05, name='', verbose=False):
    """Perform ADFuller to test for Stationarity of given series and print report"""
    r = adfuller(series, autolag='AIC')
    output = {'test_statistic':round(r[0], 4), 'pvalue':round(r[1], 4), 'n_lags':round(r[2], 4), 'n_obs':r[3]}
    p_value = output['pvalue'] 
    def adjust(val, length= 6): return str(val).ljust(length)

    # Print Summary
    print(f'    Augmented Dickey-Fuller Test on "{name}"', "\n   ", '-'*47)
    print(f' Null Hypothesis: Data has unit root. Non-Stationary.')
    print(f' Significance Level    = {signif}')
    print(f' Test Statistic        = {output["test_statistic"]}')
    print(f' No. Lags Chosen       = {output["n_lags"]}')

    for key,val in r[4].items():
        print(f' Critical value {adjust(key)} = {round(val, 3)}')

    if p_value <= signif:
        print(f" => P-Value = {p_value}. Rejecting Null Hypothesis.")
        print(f" => Series is Stationary.")
    else:
        print(f" => P-Value = {p_value}. Weak evidence to reject the Null Hypothesis.")
        print(f" => Series is Non-Stationary.")    



# ADF Test on each column
for name, column in df_train.iteritems():
    adfuller_test(column, name=column.name)
    print('\n')

The ADF test confirms none of the time series is stationary. Let’s difference all of them once and check again.
# 1st difference
df_differenced = df_train.diff().dropna()

# ADF Test on each column of 1st Differences Dataframe
for name, column in df_differenced.iteritems():
    adfuller_test(column, name=column.name)
    print('\n')


# After the first difference, Real Wages (Manufacturing) is still not stationary. It’s critical value is between 5% and 10% significance level.

# All of the series in the VAR model should have the same number of observations.

# So, we are left with one of two choices.

# That is, either proceed with 1st differenced series or difference all the series one more time.


# Second Differencing
df_differenced = df_differenced.diff().dropna()

# ADF Test on each column of 2nd Differences Dataframe
for name, column in df_differenced.iteritems():
    adfuller_test(column, name=column.name)
    print('\n')


# All the series are now stationary.

# Let’s prepare the training and test datasets.

# 10. How to Select the Order (P) of VAR model
# To select the right order of the VAR model, we iteratively fit increasing orders of VAR model and pick the order that gives a model with least AIC.

# Though the usual practice is to look at the AIC, you can also check other best fit comparison estimates of BIC, FPE and HQIC.


model = VAR(df_differenced)
for i in [1,2,3,4,5,6,7,8,9]:
    result = model.fit(i)
    print('Lag Order =', i)
    print('AIC : ', result.aic)
    print('BIC : ', result.bic)
    print('FPE : ', result.fpe)
    print('HQIC: ', result.hqic, '\n')



# In the above output, the AIC drops to lowest at lag 4, then increases at lag 5 and then continuously drops further.

# Let’s go with the lag 4 model.

# An alternate method to choose the order(p) of the VAR models is to use the model.select_order(maxlags) method.

# The selected order(p) is the order that gives the lowest ‘AIC’, ‘BIC’, ‘FPE’ and ‘HQIC’ scores.

x = model.select_order(maxlags=12)
x.summary()


# According to FPE and HQIC, the optimal lag is observed at a lag order of 3.

# I, however, don’t have an explanation for why the observed AIC and BIC values differ when using result.aic versus as seen using model.select_order().

# Since the explicitly computed AIC is the lowest at lag 4, I choose the selected order as 4.

# 11. Train the VAR Model of Selected Order(p)


model_fitted = model.fit(4)
model_fitted.summary()



# 12. Check for Serial Correlation of Residuals (Errors) using Durbin Watson Statistic
# Serial correlation of residuals is used to check if there is any leftover pattern in the residuals (errors).

# What does this mean to us?

# If there is any correlation left in the residuals, then, there is some pattern in the time series that is still left to be explained by the model. In that case, the typical course of action is to either increase the order of the model or induce more predictors into the system or look for a different algorithm to model the time series.

# So, checking for serial correlation is to ensure that the model is sufficiently able to explain the variances and patterns in the time series.

# Alright, coming back to topic.

# A common way of checking for serial correlation of errors can be measured using the Durbin Watson’s Statistic.

# The value of this statistic can vary between 0 and 4. The closer it is to the value 2, then there is no significant serial correlation. The closer to 0, there is a positive serial correlation, and the closer it is to 4 implies negative serial correlation.

