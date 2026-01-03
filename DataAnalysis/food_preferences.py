import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

df = pd.read_csv("/Users/vlad/Desktop/Food_Preference.txt")

Gender = df["Gender"].value_counts()

df["Nationality"] = df["Nationality"].replace({"MY":'Malaysian'})
df.loc[df["Nationality"].str.contains('mala', case= False),"Nationality"] ='Malaysian'
df["Nationality"] = df["Nationality"].str.rstrip()
df["Timestamp"] = df["Timestamp"].str.replace(r"\sGMT[+-]\d+", "", regex=True)
df["Timestamp"] = pd.to_datetime(df["Timestamp"],format="%Y/%m/%d %I:%M:%S %p").dt.strftime("%Y/%m/%d")

Gender = df["Gender"].value_counts()
Nationality = df["Nationality"].value_counts()

Dessert = df["Dessert"].value_counts()

Food_Day = (
    df.groupby(["Timestamp", "Food"])
    .size()
    .unstack(fill_value=0)
)

dates = Food_Day.index.astype(str)
traditional = Food_Day["Traditional food"].values
western = Food_Day["Western Food"].values

x = np.arange(len(dates))
width = 0.2


figure, axes = plt.subplots(2,2,figsize = (15,10))

axes[0,0].pie(Gender.values, labels= Gender.index, autopct="%1.1f%%")
axes[0,0].set_title('Male vs Female')
axes[0,0].set_xlabel('Gender')

axes[0,1].barh(Nationality.index, Nationality.values, edgecolor='black')
axes[0,1].set_title('Nationality')

axes[1,0].bar(x - width/2, traditional, width, label= "Traditional food", edgecolor='black')
axes[1,0].bar(x + width/2, western, width, label= "Western Food", edgecolor='black')
axes[1,0].set_xticks(x)
axes[1,0].set_xticklabels(dates)
axes[1,0].set_title("Food Count by Date")
axes[1,0].legend()

axes[1,1].bar(Dessert.index, Dessert.values, edgecolor='black')
axes[1,1].set_title('Dessert')


plt.show()

print(western)
