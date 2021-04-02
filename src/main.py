from google.cloud import bigquery_reservation_v1
from google.api_core import retry

import json

import base64
import time
import os

#import logging
#import google.cloud.logging
#from google.cloud.logging.handlers import CloudLoggingHandler, setup_logging

#logging
#client = google.cloud.logging.Client()
#handler = CloudLoggingHandler(client)
#logger = logging.getLogger()
#logger.setLevel(logging.DEBUG) # defaults to WARN
#setup_logging(handler)

res_api = bigquery_reservation_v1.ReservationServiceClient()

def bootstrap_flex_slot(event, context):
    """Triggered from a message on a Cloud Pub/Sub topic.
    Args:
         event (dict): Event payload.
         context (google.cloud.functions.Context): Metadata for the event.
    """
    start = time.time()
    pubsub_message = base64.b64decode(event['data']).decode('utf-8')
    print("topic message: " + pubsub_message)
    json_msg = json.loads(pubsub_message)
    if json_msg['flex_op'] == 'create':
        print('executing create function')
        #exec_create_flex_slot(json_msg)
    elif json_msg['flex_op'] == 'delete':
        print('executing delete function')
        #exec_delete_flex_slot(json_msg)
    end = time.time()
    print("Function ran for ~{} seconds".format((end - start)))


def exec_create_flex_slot(json_msg):
    """Triggered from a message on a Cloud Pub/Sub topic.
    Args:
         json_msg (dict): Event payload in serialized json.
    """
    project_id = json_msg['project_id']
    location = json_msg['location']
    reservation_name = json_msg['reservation_name']
    assignment_project = json_msg['assignment_project']
    commitment_slots = json_msg['commitment_slots']
    reservation_slots = json_msg['reservation_slots']
    parent_arg = "projects/{}/locations/{}".format(project_id, location)
    print("initiating bootstrap fn for flex slot")
    print("project execution: " + parent_arg)
    print("reservation name: " + reservation_name)
    print("assignment project: " + assignment_project)
    print("commitment slots: " + str(commitment_slots))
    print("reservation slots: " + str(reservation_slots))
    try:
        if commitment_slots:
            print("executing commitment")
            commit = purchase_commitment(parent_arg, int(commitment_slots))
        print("executing reservation")
        reservation = create_reservation(parent_arg, reservation_name, int(reservation_slots))
        print("executing assignment")
        assignment = create_assignment(reservation, assignment_project)
        time.sleep(60)
        print("--------------------------------")
        if commitment_slots:
            print("commit id: ", commit)
        print("res id: ", reservation)
        print("assign id: ", assignment)
        print("--------------------------------")
    except Exception as e:
        print(e)
        return


def purchase_commitment(parent_arg, slots):
    """
    Create a commitment for a specific amount of slots (in increments of 500).
    :param parent_arg: parent arg contains structure of project/x/location/x
    :param slots: Number of slots to purchase
    :return: the commit name
    """
    commit_config = bigquery_reservation_v1.CapacityCommitment(plan='FLEX', slot_count=slots)

    commit = res_api.create_capacity_commitment(parent=parent_arg,
                                                capacity_commitment=commit_config)
    return commit.name


def create_reservation(parent_arg, reservation_name, reservation_slots=100):
    """
    Create a reservation with a specific amount of slots (reservation_slots must be lower than remaining slots available).
    :param parent_arg: parent arg contains structure of project/x/location/x
    :param reservation_name: Name of the reservation.
    :param reservation_slots: Number of slots for this reservation
    :return: the reservation name
    """

    res_config = bigquery_reservation_v1.Reservation(slot_capacity=reservation_slots, ignore_idle_slots=False)
    res = res_api.create_reservation(parent=parent_arg,
                                     reservation_id=reservation_name,
                                     reservation=res_config)
    return res.name


def create_assignment(reservation_id, user_project):
    """
    Create an assignment of either an organization, folders or projects to a specific reservation.
    :param reservation_id: The reservation id from which the project id will be assigned
    :param user_project: The project id that will use be assigned to this reservation
    :return: the assignment name
    """
    assign_config = bigquery_reservation_v1.Assignment(job_type='QUERY',
                               assignee='projects/{}'.format(user_project))

    assign = res_api.create_assignment(parent=reservation_id,
                                       assignment=assign_config)
    return assign.name


def get_custom_list_ids(parent_arg):
    """
    Get custom list ids that are created for flex slots.
    :param parent_arg: parent arg contains structure of project/x/location/x
    :return: custom list of commitments, reservation, assignments
    """
    list_flex_commitments = [i.name for i in res_api.list_capacity_commitments(parent=parent_arg) if i.plan == bigquery_reservation_v1.CapacityCommitment.CommitmentPlan.FLEX]
    list_custom_reservations = [i.name for i in res_api.list_reservations(parent=parent_arg) if i.slot_capacity > 0]

    list_custom_assignments = []
    for i in list(map(lambda x: x.split("/")[-1], list_custom_reservations)):
        list_custom_assignments.extend([i.name for i in res_api.list_assignments(parent=parent_arg + "/reservations/" + i)])

    return list_flex_commitments, list_custom_reservations, list_custom_assignments


def flex_cleanup(list_flex_commitments, list_custom_reservations, list_custom_assignments):
    """
    Delete all flex commitments, reservation & assignments from the list
    :param list_flex_commitments: list with flex commitments
    :param list_custom_reservations: list with flex reservation
    :param list_custom_assignments: list with flex assignment
    """
    for i in list_custom_assignments:
        res_api.delete_assignment(name=i)
    for i in list_custom_reservations:
        res_api.delete_reservation(name=i)
    for i in list_flex_commitments:
        res_api.delete_capacity_commitment(name=i,
                                           retry=retry.Retry(deadline=90,
                                                             predicate=Exception,
                                                             maximum=2))


def exec_delete_flex_slot(json_msg):
    """
    Execute custom list of flex slots reservation to remove
    :param json_msg: json to get pub/sub parameters
    """
    project_id = json_msg['project_id']
    location = json_msg['location']
    parent_arg = "projects/{}/locations/{}".format(project_id, location)
    try:
        list_flex_commitments, list_custom_reservations, list_custom_assignments = get_custom_list_ids(parent_arg)
        print("--commitments, reservations, assignments--")
        print(list_flex_commitments)
        print(list_custom_reservations)
        print(list_custom_assignments)
        flex_cleanup(list_flex_commitments, list_custom_reservations, list_custom_assignments)
        print("all flex slots are deleted...")
    except Exception as e:
        print(e)
        return
