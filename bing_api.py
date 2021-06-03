import numpy as np
import requests
import json


#rename to CustomerData later
class Locations:
    def __init__(self, start, addresses):
        self.start = start
        self.addresses = addresses

    def all(self):        
        locations = [self.start] + self.addresses
        return locations


class Coordinates:

    def __init__(self, locations):
        self.locations = locations
    
    def calculateFromLocations(self):
        params = {
        'key' : "AvxXPVB5LQKdve9G1Dgh-1yG2uVuOvjNqzgtCZdvv2cAliLRuytKkVSk0Unh8FJt"
        }
        coordinates = []

        for address in self.locations:
            formattedAddress = self.formatAddress(address)
            r = requests.get('http://dev.virtualearth.net/REST/v1/Locations/{}'.format(formattedAddress),\
                '&maxResults=1&key={}'.format(params['key'])) 
            if r.status_code == 404:
                continue
            results = r.json() 
            #print(results)
            #print(results['resourceSets'][0]['resources'][0]['geocodePoints'][0]['coordinates'])

            try:
                assert(results['resourceSets'][0]['estimatedTotal']) 
                point = results['resourceSets'][0]['resources'][0]['geocodePoints'][0]['coordinates']
                lat, lng = point[0], point[1]
            except:
                lat,lng = None, None


            # print(results)
            
           
            # 
            #appends a dictionary of latitude and longitude points for the given address
            coordinates.append({
                "latitude": lat,
                "longitude": lng
            })
        #prints lat, long points for each address
        # for i in coordinates:
        #     print(i, "\n")
        #     print(type(i["latitude"]))

        #return array of dictionaries containing lat, long points
        return coordinates

    def formatAddress(self, address):
        output = address.replace(" ", "%20")
        return output


"""
unit can be "travelDistance" for distance or "travelDuration" for time
"""

class DistanceMatrix:
    def __init__(self, coordinates, unit = "travelDistance"):
        self.coordinates = coordinates
        self.unit = unit
    
    def calculateFromCoordinates(self):
        m = len(self.coordinates)
        
        times = m//50
        remainder = m%50

        if m < 50:
            return self.calculateBlock(0,m,0,m)
        
        rowBlock = []
        for row in range(times):
            colBlocks = []
            for col in range(times):
                x = self.calculateBlock(row*50, (row+1)*50, col*50, (col+1)*50)
                colBlocks.append(x)
            x = self.calculateBlock(row*50, (row+1)*50, times*50, (times*50)+remainder)
            colBlocks.append(x)
            y = self.joinCol(colBlocks)
            rowBlock.append(y)
        data_matrix = self.joinRow(rowBlock)
            
        return data_matrix
        
        
    def joinCol(self, arr):
        tple = tuple(i for i in arr)
        output = np.concatenate(tple,1).tolist()
        return output
    def joinRow(self, arr):
        tple = tuple(i for i in arr)
        output = np.concatenate(tple,0).tolist()
        return output
            
    def calculateBlock(self, fromStart, fromEnd, toStart, toEnd):
        params = {
        'key' : "AvxXPVB5LQKdve9G1Dgh-1yG2uVuOvjNqzgtCZdvv2cAliLRuytKkVSk0Unh8FJt"
        }

        post_json = {
            "origins": self.coordinates[fromStart:fromEnd],
            "destinations": self.coordinates[toStart:toEnd],
            "travelMode": "driving"
        }

        r = requests.post('https://dev.virtualearth.net/REST/v1/Routes/DistanceMatrix',
                params=params, json=post_json)
        data_results = r.json()
        data_results = data_results["resourceSets"][0]["resources"][0]["results"]

        data = [
            data_results[i][self.unit] for i in range(len(data_results))
        ]

        n = fromEnd - fromStart
        m = toEnd - toStart
        data_matrix_block = [[0 for i in range(m)] for i in range(n)]

        for i in data_results:
                to = i["destinationIndex"]
                frm = i["originIndex"]
                dist = i[self.unit]
                data_matrix_block[frm][to] = dist


        return data_matrix_block
