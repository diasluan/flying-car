import argparse
import time
from enum import Enum

import numpy as np

from udacidrone import Drone
from udacidrone.connection import MavlinkConnection
from udacidrone.messaging import MsgID


class States(Enum):
    MANUAL = 0
    ARMING = 1
    TAKEOFF = 2
    WAYPOINT = 3
    LANDING = 4
    DISARMING = 5


class BackyardFlyer(Drone):

    def __init__(self, connection):
        super().__init__(connection)
        self.target_position = np.array([0.0, 0.0, 0.0])
        self.all_waypoints = self.calculate_box()
        self.in_mission = True
        self.check_state = {}

        # initial state
        self.flight_state = States.MANUAL
        self.target_precision = 0.1

        # TODO: Register all your callbacks here
        self.register_callback(MsgID.LOCAL_POSITION, self.local_position_callback)
        self.register_callback(MsgID.LOCAL_VELOCITY, self.velocity_callback)
        self.register_callback(MsgID.STATE, self.state_callback)

    def local_position_callback(self):
        if self.flight_state == States.TAKEOFF:
            altitude = -1.0 * self.local_position[2]
            
            if (self.target_position[2] - altitude) < self.target_precision:
                self.waypoint_transition()
        
        if self.flight_state == States.WAYPOINT:
            if self.reached_target():
                if self.all_waypoints == []:
                    self.landing_transition()
                else:
                    self.waypoint_transition()

    def velocity_callback(self):
        if self.flight_state == States.LANDING:
            if ((self.global_position[2] - self.global_home[2] < 0.1) and
            abs(self.local_position[2]) < self.target_precision):
                self.disarming_transition()

    def state_callback(self):
        if not self.in_mission:
            return
        if self.flight_state == States.MANUAL: self.arming_transition()
        elif self.flight_state == States.ARMING: self.takeoff_transition()
        elif self.flight_state == States.DISARMING: self.manual_transition()

    def calculate_box(self, size=10.0):
        """TODO: Fill out this method
        
        1. Return waypoints to fly a box
        """
        return  [[self.global_home[0]+size, self.global_home[1], self.global_home[2]+3.0],
                 [self.global_home[0]+size, self.global_home[1]+size, self.global_home[2]+3.0],
                 [self.global_home[0], self.global_home[1]+size, self.global_home[2]+3.0],
                 [self.global_home[0], self.global_home[1], self.global_home[2]+3.0] ]

    def arming_transition(self):
        print("arming transition")
        self.take_control()
        self.arm()

        self.set_home_position(self.global_position[0],
                               self.global_position[1],
                               self.global_position[2])
        self.flight_state = States.ARMING

    def takeoff_transition(self, target_altitude=3.0):
        """TODO: Fill out this method
        
        1. Set target_position altitude to 3.0m
        2. Command a takeoff to 3.0m
        3. Transition to the TAKEOFF state
        """
        print("takeoff transition")
        self.target_position[2] = target_altitude
        self.takeoff(target_altitude)
        self.flight_state = States.TAKEOFF


    def waypoint_transition(self):
        """TODO: Fill out this method
    
        1. Command the next waypoint position
        2. Transition to WAYPOINT state
        """
        print("waypoint transition")
        self.target_position = self.all_waypoints.pop(0)
        self.cmd_position(self.target_position[0], self.target_position[1], self.target_position[2], 0)
        self.flight_state = States.WAYPOINT


    def landing_transition(self):
        """TODO: Fill out this method
        
        1. Command the drone to land
        2. Transition to the LANDING state
        """
        print("landing transition")
        self.land()
        self.flight_state = States.LANDING

    def disarming_transition(self):
        """TODO: Fill out this method
        
        1. Command the drone to disarm
        2. Transition to the DISARMING state
        """
        print("disarm transition")
        self.disarm()
        self.flight_state = States.DISARMING

    def manual_transition(self):
        """This method is provided
        
        1. Release control of the drone
        2. Stop the connection (and telemetry log)
        3. End the mission
        4. Transition to the MANUAL state
        """
        print("manual transition")

        self.release_control()
        self.stop()
        self.in_mission = False
        self.flight_state = States.MANUAL

    def start(self):
        """This method is provided
        
        1. Open a log file
        2. Start the drone connection
        3. Close the log file
        """
        print("Creating log file")
        self.start_log("Logs", "NavLog.txt")
        print("starting connection")
        self.connection.start()
        print("Closing log file")
        self.stop_log()

    def reached_target(self):
        x_0, y_0, z_0 = self.local_position[0], self.local_position[1], -self.local_position[2]
        x_1, y_1, z_1 = self.target_position[0], self.target_position[1], self.target_position[2]
        return self.target_precision > ((x_1-x_0)**2 + (y_1-y_0)**2 + (z_1-z_0)**2)**(1/2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=5760, help='Port number')
    parser.add_argument('--host', type=str, default='127.0.0.1', help="host address, i.e. '127.0.0.1'")
    args = parser.parse_args()

    conn = MavlinkConnection('tcp:{0}:{1}'.format(args.host, args.port), threaded=False, PX4=False)
    drone = BackyardFlyer(conn)
    time.sleep(2)
    drone.start()