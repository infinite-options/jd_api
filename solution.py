from __future__ import print_function
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp



class DistanceConstraintSolution:

    def __init__(self, dataMatrix, num_vehicles):
        self.dataMatrix = dataMatrix
        self.num_vehicles = num_vehicles


    def create_data_model(self):
        """Stores the data for the problem."""
        data = {}
        data['distance_matrix'] = self.dataMatrix
        data['num_vehicles'] = self.num_vehicles
        data['depot'] = 0
        return data

    def get_solution(self, data,manager,routing,solution):
        solution_data = {'result':[] , 'route_dist':[]}
        result = []
        
        max_route_distance = 0

        for vehicle_id in range(data['num_vehicles']):
            index = routing.Start(vehicle_id)
            # plan_output = 'Route for vehicle {}:\n'.format(vehicle_id)
            route_distance = 0
            driver_plan = []
            while not routing.IsEnd(index):
                # plan_output += ' {} -> '.format(manager.IndexToNode(index))
                driver_plan.append(manager.IndexToNode(index))

                previous_index = index

                index = solution.Value(routing.NextVar(index))
                route_distance += routing.GetArcCostForVehicle(
                    previous_index, index, vehicle_id)
            # plan_output += '{}\n'.format(manager.IndexToNode(index))
            driver_plan.append(manager.IndexToNode(index))
            # result.append(driver_plan)
            solution_data['result'].append(driver_plan)
            solution_data['route_dist'].append(route_distance)
            # plan_output += 'Distance of the route: {}m\n'.format(route_distance)
            max_route_distance = max(route_distance, max_route_distance)

        return solution_data


    def print_solution(self, data, manager, routing, solution):
        """Prints solution on console."""
        max_route_distance = 0


        for vehicle_id in range(data['num_vehicles']):
            index = routing.Start(vehicle_id)
            plan_output = 'Route for vehicle {}:\n'.format(vehicle_id)
            route_distance = 0

            while not routing.IsEnd(index):
                plan_output += ' {} -> '.format(manager.IndexToNode(index))
                # print("TO NODE ",manager.IndexToNode(index))

                previous_index = index
                # print("index: ", index)
                index = solution.Value(routing.NextVar(index))
                route_distance += routing.GetArcCostForVehicle(
                    previous_index, index, vehicle_id)
                # print("previous index = {} ; index = {} ; vehicle_id = {}".format(previous_index, index, vehicle_id))
                # print("route_distance: ", route_distance)
            plan_output += '{}\n'.format(manager.IndexToNode(index))
            

            plan_output += 'Distance of the route: {}m\n'.format(route_distance)
            print(plan_output)
            max_route_distance = max(route_distance, max_route_distance)

        print('Maximum of the route distances: {}m'.format(max_route_distance))

    def solve(self):
        """Solve the CVRP problem."""
        # Instantiate the data problem.
        data = self.create_data_model()

        # Create the routing index manager.
        manager = pywrapcp.RoutingIndexManager(len(data['distance_matrix']),
                                            data['num_vehicles'], data['depot'])

        # Create Routing Model.
        routing = pywrapcp.RoutingModel(manager)


        # Create and register a transit callback.
        def distance_callback(from_index, to_index):
            """Returns the distance between the two nodes."""
            # Convert from routing variable Index to distance matrix NodeIndex.
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return data['distance_matrix'][from_node][to_node]

        transit_callback_index = routing.RegisterTransitCallback(distance_callback)

        # Define cost of each arc.
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

        # dimension_name = 'Distance'
        # routing.AddDimension(
        #     transit_callback_index,
        #     0,  # no slack
        #     1000000,  # vehicle maximum travel distance
        #     True,  # start cumul to zero
        #     dimension_name)
        # distance_dimension = routing.GetDimensionOrDie(dimension_name)
        # distance_dimension.SetGlobalSpanCostCoefficient(10)

        # num_vehicles = data['num_vehicles']
        # num_nodes = len(data['distance_matrix'])
        # print(num_nodes//num_vehicles + 1)
        # count_dimension_name = 'count'
        # # # assume some variable num_nodes holds the total number of nodes
        # routing.AddConstantDimension(
        #     1, # increment by one every time
        #     num_nodes // num_vehicles + 1,  # max value forces equivalent # of jobs
        #     True,  # set count to zero
        #     count_dimension_name)
        # count_dimension = routing.GetDimensionOrDie(count_dimension_name)

        # Setting first solution heuristic.
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.time_limit.seconds = 10
        search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)

        # Solve the problem.
        solution = routing.SolveWithParameters(search_parameters)
        # Print solution on console.
        addresses_in_order = []
        if solution:
            self.print_solution(data, manager, routing, solution)
            sol = self.get_solution(data, manager, routing, solution)
            print("sol 1: \n", sol)

            return sol

        

        




