import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

class Kmeans:
    def __init__(self, k, tol=0.001, max_iter=1000):
        self.k = k
        self.tol = tol
        self.max_iter = max_iter

    def fit(self,data):

        self.centers = {}

        #Initial centers are first k points of data array
        for i in range(self.k):
            self.centers[i] = data[i]
            

        for i in range(self.max_iter):
            self.labels = {}

            for i in range(self.k):
                self.labels[i] = []

            for thing in data:
                #Calculate a vector of distances of data point to center of each cluster
                distances = [np.linalg.norm(thing-self.centers[center]) for center in self.centers]
                #The cluster which the data point belongs is where it is the closest to the center of that cluster
                label = distances.index(min(distances))
                self.labels[label].append(thing)
                

            prev_centers = dict(self.centers)
            
            #Recalculate centers 
            for label in self.labels:
                self.centers[label] = np.average(self.labels[label],axis=0)

            optimized = True

            for c in self.centers:
                original_center = prev_centers[c]
                current_center = self.centers[c]
                #If centers are still moving, rerun algorithm
                if np.sum((current_center-original_center)/original_center*100.0) > self.tol:
                    optimized = False

            if optimized:
                break


# coordinates = [{'latitude': 37.317469, 'longitude': -122.019218}, {'latitude': 37.21281, 'longitude': -121.87598}, {'latitude': 37.21026, 'longitude': -121.82815}, {'latitude': 37.226068, 'longitude': -121.861264}, {'latitude': 37.20098, 'longitude': -121.85874}, {'latitude': 37.227124, 'longitude': -121.886943}, {'latitude': 37.22025, 'longitude': -121.86673}, {'latitude': 37.282141, 'longitude': -121.859561}, {'latitude': 37.199313, 'longitude': -121.829092}, {'latitude': 37.222307, 'longitude': -121.890135}, {'latitude': 37.22985, 'longitude': -121.8908}, {'latitude': 37.212021, 'longitude': -121.840744}, {'latitude': 37.221648, 'longitude': -121.876}, {'latitude': 37.220293, 'longitude': -121.872801}, {'latitude': 37.22793, 'longitude': -121.89493}, {'latitude': 37.20539, 'longitude': -121.83414}, {'latitude': 37.2098, 'longitude': -121.84869}, {'latitude': 37.21019, 'longitude': -121.87221}, {'latitude': 37.20666, 'longitude': -121.845314}, {'latitude': 37.20921, 'longitude': -121.86601}, {'latitude': 37.199574, 'longitude': -121.837836}, {'latitude': 37.22274, 'longitude': -121.84977}, {'latitude': 37.22002, 'longitude': -121.84682}, {'latitude': 37.206714, 'longitude': -121.858709}, {'latitude': 37.231342, 'longitude': -121.891046}, {'latitude': 37.21001, 'longitude': -121.82328}, {'latitude': 37.195659, 'longitude': -121.843228}, {'latitude': 37.20447, 'longitude': -121.8289}, {'latitude': 37.3381255, 'longitude': -122.0300825}, {'latitude': 37.20697, 'longitude': -121.87237}, {'latitude': 37.23602, 'longitude': -121.87142}, {'latitude': 36.96344117, 'longitude': -122.05851283}, {'latitude': 37.21958, 'longitude': -121.87582}, {'latitude': 37.22055, 'longitude': -121.89293}, {'latitude': 37.22168, 'longitude': -121.89274}, {'latitude': 37.21393, 'longitude': -121.87324}, {'latitude': 37.31781, 'longitude': -122.06542}, {'latitude': 37.235976, 'longitude': -121.810059}, {'latitude': 37.203119, 'longitude': -121.857549}, {'latitude': 37.235542, 'longitude': -121.848751}, {'latitude': 37.200639, 'longitude': -121.836549}, {'latitude': 37.23312, 'longitude': -121.88238}, {'latitude': 37.20893, 'longitude': -121.85216}, {'latitude': 37.204775, 'longitude': -121.831414}, {'latitude': 37.21856, 'longitude': -121.85627}, {'latitude': 37.20588, 'longitude': -121.82793}, {'latitude': 37.22775, 'longitude': -121.86722}, {'latitude': 37.22524, 'longitude': -121.866181}, {'latitude': 37.20447, 'longitude': -121.8289}]
# coordinates = [{'latitude': 30.27657, 'longitude': -97.68505}, {'latitude': 30.29189, 'longitude': -97.72309}, {'latitude': 30.28613783, 'longitude': -97.74839433}, {'latitude': 30.25452, 'longitude': -97.743555}, {'latitude': 30.37651633, 'longitude': -97.78143783}, {'latitude': 30.23926, 'longitude': -97.74185}, {'latitude': 30.18962, 'longitude': -97.79325}, {'latitude': 30.24829, 'longitude': -97.76095}, {'latitude': 30.238587, 'longitude': -97.854023}, {'latitude': 30.23099, 'longitude': -97.77633}, {'latitude': 30.239882, 'longitude': -97.732218}, {'latitude': 30.402666, 'longitude': -97.741423}, {'latitude': 30.22379, 'longitude': -97.73543}, {'latitude': 30.333277, 'longitude': -97.560102}, {'latitude': 30.34557983, 'longitude': -97.73374883}, {'latitude': 30.33932, 'longitude': -97.75127}, {'latitude': 30.214492, 'longitude': -97.870316}, {'latitude': 30.4214, 'longitude': -97.69614}, {'latitude': 30.35849, 'longitude': -97.72837}, {'latitude': 30.427291, 'longitude': -97.68265}, {'latitude': 30.24944, 'longitude': -97.78423}, {'latitude': 30.31876, 'longitude': -97.742065}, {'latitude': 30.394376, 'longitude': -97.725481}, {'latitude': 30.23238, 'longitude': -97.90939}, {'latitude': 30.421767, 'longitude': -97.694001}, {'latitude': 30.24539, 'longitude': -97.68412}, {'latitude': 30.264846, 'longitude': -97.744214}, {'latitude': 30.438205, 'longitude': -97.674767}, {'latitude': 30.366892, 'longitude': -97.792987}, {'latitude': 30.17486, 'longitude': -97.79691}, {'latitude': 30.23530333, 'longitude': -97.71271833}, {'latitude': 30.233217, 'longitude': -97.76482}, {'latitude': 30.18287, 'longitude': -97.81968}, {'latitude': 30.29187, 'longitude': -97.70007}, {'latitude': 30.29245, 'longitude': -97.699994}, {'latitude': 30.30156, 'longitude': -97.75096}, {'latitude': 30.38676, 
# 'longitude': -97.65582}, {'latitude': 30.24525, 'longitude': -97.75426}, {'latitude': 30.30047, 'longitude': -97.67625}, {'latitude': 30.37996967, 'longitude': -97.770365}, {'latitude': 30.293985, 'longitude': -97.704886}, {'latitude': 30.28267383, 'longitude': -97.74639217}, {'latitude': 30.2047, 'longitude': -97.86968}, {'latitude': 30.24856, 'longitude': -97.87503}, {'latitude': 30.18997, 'longitude': -98.0374}, {'latitude': 30.19073, 'longitude': -97.81217}, {'latitude': 30.28042, 'longitude': -97.79799}, {'latitude': 30.31781, 'longitude': -97.69872}, {'latitude': 30.28843, 'longitude': -97.71928}, {'latitude': 30.22887, 'longitude': -97.76211}, {'latitude': 30.23865, 'longitude': -97.76508}, {'latitude': 30.26254, 'longitude': -97.76191}, {'latitude': 30.312333, 'longitude': -97.696797}, {'latitude': 30.33742, 'longitude': -97.8109}, {'latitude': 30.29068, 'longitude': -97.700515}, {'latitude': 30.306536, 'longitude': -97.752095}, {'latitude': 30.29703317, 'longitude': -97.7004955}, {'latitude': 30.29716, 'longitude': -97.69985}, {'latitude': 30.26351, 'longitude': -97.87934}, {'latitude': 30.42016, 'longitude': -97.73153}, {'latitude': 30.27939, 'longitude': -97.71537}, {'latitude': 30.34088067, 'longitude': -97.78347567}, {'latitude': 30.298926, 'longitude': -97.707926}, {'latitude': 30.268931, 'longitude': -97.753224}, 
# {'latitude': 30.20599, 'longitude': -97.78094}, {'latitude': 30.37733, 'longitude': -97.74779}, {'latitude': 30.28425, 'longitude': -97.87598}, {'latitude': 30.35752, 'longitude': -97.76575}, {'latitude': 30.2399, 'longitude': -97.76577}, {'latitude': 30.1644050218171, 'longitude': -97.8863264286856}, {'latitude': 30.21744, 'longitude': -97.89233}, {'latitude': 30.30903, 'longitude': -97.69694}, {'latitude': 30.23825217, 'longitude': -97.79043417}, {'latitude': 30.284455, 'longitude': -97.720995}, {'latitude': 30.27305, 'longitude': -97.72954}, {'latitude': 30.25750367, 'longitude': -97.77271533}, {'latitude': 30.23662633, 'longitude': -97.7637}, {'latitude': 30.214336, 'longitude': -97.88965}, {'latitude': 30.4222, 'longitude': -97.72505}, {'latitude': 30.273695, 'longitude': -97.74727167}, {'latitude': 30.26010167, 'longitude': -97.68292167}, {'latitude': 30.22562, 'longitude': -97.69487}, {'latitude': 30.35681, 'longitude': -97.76393}, {'latitude': 30.35701, 'longitude': -98.01034}, {'latitude': 30.395421, 'longitude': -97.727591}, {'latitude': 30.25974, 'longitude': -97.748877}, {'latitude': 30.27474, 'longitude': -97.72172}, {'latitude': 30.295383, 'longitude': -97.871094}, {'latitude': 30.27784, 'longitude': -97.842731}, {'latitude': 30.249656, 'longitude': -97.793848}, {'latitude': 30.22926033, 'longitude': -97.82609483}, {'latitude': 30.27859, 'longitude': -97.75263}, {'latitude': 30.30991, 'longitude': -97.72657}, {'latitude': 30.25570517, 'longitude': -97.74298833}, {'latitude': 30.21901517, 'longitude': -97.90460917}, {'latitude': 30.25265, 'longitude': -97.77128}, {'latitude': 30.25648, 'longitude': -97.67042}, {'latitude': 30.238394, 'longitude': -97.74006283}, {'latitude': 30.23173233, 'longitude': -97.83733317}, {'latitude': 30.27781, 'longitude': -97.76671}, {'latitude': 30.236192, 'longitude': -97.767871}, {'latitude': 30.45042, 'longitude': -97.77894}, {'latitude': 30.20604, 'longitude': -97.88472}, {'latitude': 30.24064, 'longitude': -97.6924}, {'latitude': 30.193751, 'longitude': -97.833232}, {'latitude': 30.31931, 'longitude': -97.71989}, {'latitude': 30.23252, 'longitude': -97.90689}, {'latitude': 30.251775, 'longitude': -97.757567}, {'latitude': 30.24002, 'longitude': -97.93467}, {'latitude': 30.21439, 'longitude': -97.80884}, {'latitude': 30.29331, 'longitude': -97.70817}, {'latitude': 30.273951, 'longitude': -97.793064}, {'latitude': 30.26777333, 'longitude': -97.75120833}, {'latitude': 30.30975, 'longitude': -97.75407}, {'latitude': 30.40444, 'longitude': -97.76541}, {'latitude': 30.23122, 'longitude': -97.77171}, {'latitude': 30.080375, 'longitude': -97.810324}, {'latitude': 30.37028583, 'longitude': -97.8076365}, {'latitude': 30.33649, 'longitude': -97.76091}, {'latitude': 30.398998, 'longitude': -97.723598}, {'latitude': 30.25302, 'longitude': -97.771822}, {'latitude': 30.2585, 'longitude': -97.71295}, {'latitude': 30.197911, 'longitude': -97.811867}, {'latitude': 30.243153, 'longitude': -97.77673}, {'latitude': 30.34602, 'longitude': -97.70242}, {'latitude': 30.223911, 'longitude': -97.953563}, {'latitude': 30.244592, 'longitude': -97.764058}, {'latitude': 30.394376, 'longitude': -97.725481}, {'latitude': 30.31375, 'longitude': -97.7452}, {'latitude': 30.257266, 'longitude': -97.73908}, {'latitude': 30.265321, 'longitude': -97.749521}, {'latitude': 30.268931, 'longitude': -97.753224}, {'latitude': 30.21301, 'longitude': -97.769573}, {'latitude': 30.282328, 'longitude': -97.809052}, {'latitude': 30.302065, 'longitude': -97.701854}, {'latitude': 30.28262, 'longitude': -97.76325}, {'latitude': 30.3829, 'longitude': -97.74769}, {'latitude': 30.18108, 'longitude': -97.89337}, {'latitude': 30.24194, 'longitude': -97.73368}, {'latitude': 30.2278485, 'longitude': -97.8285595}, {'latitude': 30.28143, 'longitude': -97.80664}, {'latitude': 30.271858, 'longitude': -97.753198}, {'latitude': 30.26900733, 'longitude': -97.75420467}, {'latitude': 30.25938517, 'longitude': -97.75678217}, {'latitude': 30.156632, 'longitude': -97.804773}, {'latitude': 30.38458, 'longitude': -97.83182}, {'latitude': 30.247068, 'longitude': -97.846258}, {'latitude': 30.236084, 'longitude': -97.772672}, {'latitude': 30.23115, 'longitude': -97.7131}, {'latitude': 30.3972, 'longitude': -97.6509}, {'latitude': 30.25058333, 'longitude': -97.77259}, {'latitude': 30.244148, 'longitude': -97.818267}, {'latitude': 30.23822367, 'longitude': -97.78675833}, {'latitude': 30.197423, 'longitude': -97.917315}, {'latitude': 30.35895, 'longitude': -97.75476}, {'latitude': 30.24127, 'longitude': -98.07174}, {'latitude': 30.316734, 'longitude': -97.780364}, {'latitude': 30.224851, 'longitude': -97.90254}, {'latitude': 30.25116, 'longitude': -97.77195}, {'latitude': 30.30568, 'longitude': -97.68168}, {'latitude': 30.244891, 'longitude': -97.766132}, {'latitude': 30.36079, 'longitude': -97.72291}, {'latitude': 30.362014, 'longitude': -97.745852}, {'latitude': 30.260484, 'longitude': -97.723743}, {'latitude': 30.38354, 'longitude': -97.76394}, {'latitude': 30.35873, 'longitude': -97.68213}, {'latitude': 30.244878, 'longitude': -97.738627}, {'latitude': 30.25938517, 'longitude': -97.75678217}, {'latitude': 30.244148, 'longitude': -97.818267}, {'latitude': 30.22113, 'longitude': -97.92884}, {'latitude': 30.33234, 'longitude': -97.76402}, {'latitude': 30.3629, 'longitude': -97.71001}, {'latitude': 30.282833, 'longitude': -97.775143}, {'latitude': 30.21476, 'longitude': -97.80699}, {'latitude': 30.23402167, 'longitude': -97.790894}, {'latitude': 30.202351, 'longitude': -97.834415}, {'latitude': 30.27409, 'longitude': -97.69564}, {'latitude': 30.278913, 'longitude': -97.761885}, {'latitude': 30.257095, 'longitude': -97.73977333}, {'latitude': 30.33498, 'longitude': -97.72926}, {'latitude': 30.491, 'longitude': -97.70239}, {'latitude': 30.154935, 'longitude': -97.745101}, {'latitude': 30.42246933, 'longitude': -97.709553}, {'latitude': 30.404, 'longitude': -97.72087}, {'latitude': 30.228023, 'longitude': -97.846845}, {'latitude': 30.239536, 'longitude': -97.78649617}, {'latitude': 30.29418, 'longitude': -97.69698}, {'latitude': 30.31314167, 'longitude': -97.69391833}, {'latitude': 30.29561, 'longitude': -97.76306}, {'latitude': 30.16949, 'longitude': -97.81844}, {'latitude': 30.240907, 'longitude': -97.7780805}, {'latitude': 30.26254, 'longitude': -97.76191}, {'latitude': 30.29507, 'longitude': -97.702477}, {'latitude': 30.32573, 'longitude': -97.77069}, {'latitude': 30.27835, 'longitude': -97.68888}, {'latitude': 30.31049, 'longitude': -97.75333}, {'latitude': 30.31784, 'longitude': -97.66688}, {'latitude': 30.31269, 'longitude': -97.86531}]
# coords_dict = {'latitude':[], 'longitude':[]}
# for i in coordinates:
#     coords_dict['latitude'].append(i['latitude'])
#     coords_dict['longitude'].append(i['longitude'])

# df = pd.DataFrame.from_dict(coords_dict)
# coords = df.to_numpy()
# #print(coords)
# kmeans = Kmeans(7)
# kmeans.fit(coords)
# colors = 100*["g","r","c","b","k"]
# for center in kmeans.centers:
#     plt.scatter(kmeans.centers[center][0], kmeans.centers[center][1],  marker = 'x')

# for label in kmeans.labels:
#     color = colors[label]
#     for i in kmeans.labels[label]:
#         plt.scatter(i[0], i[1], color=color,  alpha = 0.5)
        
# plt.show()

