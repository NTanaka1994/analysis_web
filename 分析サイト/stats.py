import statsmodels.formula.api as smf
import statsmodels.api as sm

import pandas as pd

df = pd.read_csv("boston.csv")
X = sm.add_constant(df.drop("PRICE", axis=1))
model = sm.OLS(df["PRICE"], X).fit()
print(model.summary())