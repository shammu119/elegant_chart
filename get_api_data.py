import requests
import pandas as pd
import openpyxl


def get_series_df(series_id):
    token = "89024|EGSh14cOpdLPlmhd4go07rubE14Bil9XAhvk44Lz"

    def bearer_oauth(r):
        r.headers["Authorization"] = f"Bearer {token}"
        return r

    url = f"https://database.mma.gov.mv/api/series?ids={series_id}"
    response = requests.get(url, auth=bearer_oauth, verify=False)
    response.raise_for_status()

    json_data = response.json()

    series_list = json_data.get("data", [])
    if not series_list:
        return pd.DataFrame()

    series = series_list[0]
    return pd.DataFrame(series.get("data", []))


api_data = get_series_df(2307)


saved_file = api_data.to_excel("data.xlsx", index=False)
