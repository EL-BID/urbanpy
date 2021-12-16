import unittest
import sys
import pandas as pd

sys.path.append('../urbanpy')
import urbanpy as up

class DownloadTests(unittest.TestCase):
    
    country = 'peru'

    def search_hdx_test(self):
        datasets = up.download.search_hdx_dataset(country)
        self.assertEqual(14, len(datasets))
    
    def download_hdx_test(self):
        # df = up.download.download_hdx_dataset(country, 0)

        # test_df = pd.DataFrame([\
        # [-18.339306, -70.382361, 11.318147, 12.099885],\
        # [-18.335694, -70.393750, 11.318147, 12.099885],\
        # [-18.335694, -70.387361, 11.318147, 12.099885],\
        # [-18.335417, -70.394028, 11.318147, 12.099885],\
        # [-18.335139, -70.394306, 11.318147, 12.099885]]\, 
        # columns=['latitude', 'longitude', 'population_2015', 'population_2020'])

        # self.assertEqual(df, test_df)

if __name__ == "__main__":
    unittest.main()
