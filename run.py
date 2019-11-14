
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import os
import streamlit as st
import sys

sys.path.insert(0, 'lib/')

from decompose_series import decompose_series
from file_selector import file_selector
from find_acf_pacf import find_acf_pacf
from generate_code import generate_code
from grid_search_arima import grid_search_arima
from mean_abs_pct_error import mean_abs_pct_error
from plot_forecast import plot_forecasts
from predict_set import predict_set
from sidebar_menus import sidebar_menus
from test_stationary import test_stationary
from train_ts_model import train_ts_model
from transform_time_series import transform_time_series

pd.set_option('display.float_format', lambda x: '%.3f' % x) # Granting that pandas won't use scientific notation for floating fields

description =   '''
                **Alchemy** is an open-source project that will help you to forecast the future from historical data. 
                It uses statiscal models and artificial intelligence to give you accurated predictions, and it's helpful for 
                financial data, network traffic, sales, and much more.
                '''

# Description
st.title('Project Alchemy 🧙‍♀️')
st.write('*An equivalent exchange: you give me data, I give you answers*')
st.write(description)

### SIDEBAR
st.sidebar.title('Your data')

upload_file = st.sidebar.button('Upload file')

if upload_file:
    filename, df = file_selector()
else:
    filename, df = file_selector(ignore_upload=True)

st.markdown('### First lines of your data')
st.dataframe(df.head()) # First lines of DataFrame

ds_column, y, data_frequency, test_set_size, exog_variables = sidebar_menus('feature_target', df=df)

# Name of the exogenous variables
exog_variables_names = exog_variables

# If there's not exogenous variables, it returns None
exog_variables = df[exog_variables] if len(exog_variables) > 0 else None

# Show plots
plot_menu_title = st.sidebar.markdown('### Charts')
plot_menu_text = st.sidebar.text('Select which charts you want to see')
show_absolute_plot = sidebar_menus('absolute')
show_seasonal_decompose = sidebar_menus('seasonal')
show_adfuller_test = sidebar_menus('adfuller')
show_train_prediction = sidebar_menus('train_predictions')
show_test_prediction = sidebar_menus('test_predictions')
plot_adfuller_result = False

if show_adfuller_test:
    plot_adfuller_result = True

# Show the historical plot?
if show_absolute_plot:
    st.markdown('# Historical data ')
    df.plot(grid=True)
    plt.title('Absolute historical data')
    st.pyplot()

# Transform DataFrame to a Series
df = transform_time_series(df, ds_column)

# Show decomposition plot
if show_seasonal_decompose:
    st.markdown('# Seasonal decomposition')
    decompose_series(df)

# Checking for stationarity in the series
st.title('Checking stationarity')
ts, d, D, seasonality, acf_pacf_data, transformation_function, test_stationarity_code = test_stationary(df[y], plot_adfuller_result, data_frequency)

st.markdown('**Data after stationary test**')
show_stationary_data = st.checkbox('Show data')
if show_stationary_data:
    st.dataframe(ts)

st.title('ACF and PACF estimation')
p, q, P, Q = find_acf_pacf(acf_pacf_data, seasonality)
st.markdown('**Suggested parameters for your model**: {}x{}{}'.format((p, d, q), (P, D, Q), (seasonality)))

st.title('Time to train!')
st.write('Select the terms on the side bar and click "Do your Magic!" button')
p, d, q, P, D, Q, s, train_model, periods_to_forecast, execute_grid_search = sidebar_menus('terms', test_set_size, seasonality, (p, d, q, P, D, Q, seasonality), df=ts)

# If train button has be clicked 
if train_model:
    exog_train = None
    exog_test = None

    # Aligning endog and exog variables index, if exog_variables is not null
    if type(exog_variables) == type(pd.DataFrame()):
        exog_variables.index = ts.index
        exog_train = exog_variables.iloc[:-test_set_size]
        exog_test = exog_variables.iloc[-test_set_size:]

    train_set = transformation_function(ts.iloc[:-test_set_size])

    test_set = transformation_function(ts.iloc[-test_set_size:])
    
    model = train_ts_model(train_set, p, d, q, P, D, Q, s, exog_variables=exog_train, quiet=False)
    final_model = train_ts_model(transformation_function(ts), p, d, q, P, D, Q, s, exog_variables=exog_variables, quiet=True)

    st.markdown('## **Train set prediction**')
    st.write('The model was trained with this data. It\'s trying to predict the same data')
    if transformation_function == np.log:
        predict_set(train_set.iloc[-24:], y, seasonality, np.exp, model, show_train_prediction=show_train_prediction, show_test_prediction=show_test_prediction)
    else:
        predict_set(train_set.iloc[-24:], y, seasonality, transformation_function, model, show_train_prediction=show_train_prediction, show_test_prediction=show_test_prediction)
    
    st.markdown('## **Test set forecast**')
    st.write('Unseen data. The model was not trained with this data and it\'s trying to forecast')
    if transformation_function == np.log:
        predict_set(test_set, y, seasonality, np.exp, model, exog_variables=exog_test,forecast=True, show_train_prediction=show_train_prediction, show_test_prediction=show_test_prediction)
    else:
        predict_set(test_set, y, seasonality, transformation_function, model, exog_variables=exog_test, forecast=True, show_train_prediction=show_train_prediction, show_test_prediction=show_test_prediction)

    # Executing Grid Search
    if execute_grid_search:
        st.markdown('# Executing Grid Search')
        st.markdown('''
                    We\'re going to find the best parameters for your model. This might take some minutes. 
                    Now it's a good time to grab some coffee.
                    ''')
        p, d, q, P, D, Q, s = grid_search_arima(train_set, exog_train,  range(p+3), range(q+3), range(P+3), range(Q+3), d=d, D=D, s=s)

    # Forecasting data
    st.markdown('# Out-of-sample Forecast')
    
    if type(exog_variables) == type(pd.DataFrame()):
        st.write('You are using exogenous variables. We can\'t forecast the future since we don\'t have the exogenous variables for future periods. Adapt the code below to use them.' )
    else:
        if transformation_function == np.log:
            forecasts = np.exp(final_model.forecast(periods_to_forecast))
            confidence_interval = np.exp(final_model.get_forecast(periods_to_forecast).conf_int())

        else:
            forecasts = final_model.forecast(periods_to_forecast)
            confidence_interval = final_model.get_forecast(periods_to_forecast).conf_int()

        confidence_interval.columns = ['ci_lower', 'ci_upper']
        plot_forecasts(forecasts, confidence_interval, data_frequency)

    st.write('# Here\'s your code')
    st.markdown(generate_code(filename, ds_column, y, test_stationarity_code, test_set_size, 
                              seasonality, p, d, q, P, D, Q, s, exog_variables_names, transformation_function, 
                              periods_to_forecast, data_frequency))