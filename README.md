# BIGQUERY FLEX SLOT OPTIMIZATION #

This repository is created to experimentally add/remove slots on bigquery with custom commitments, reservations & assignments using bigquery flex slot reservation concepts. For more information refer to the [bigquery reservation](https://cloud.google.com/bigquery/docs/reservations-intro)

- **Flex Slot commitments** are purchases charged in increments of 100 slot hours for $4, or ~$0.33/minute. You can increase your slot commitments if you need faster queries or more concurrency.  
- **Reservations** create a named allocation of slots, and are necessary to assign purchased slots to a project. Find details on reservations in this documentation.
- **Assignments** assign reservations to Organizations, Folders, or Projects. All queries in a project will switch from on-demand billing to purchased slots after the assignment is made.`

![alt text](https://cloud.google.com/bigquery/images/reservations-concepts.svg)

Bigquery offers several commitment plans such as Monthly, Annual & Flex. This code is built to add & remove flex slots in an automated way using pub/sub triggered cloud function.

**pub/sub payload:** 
How to create the flex slots?
`{"flex_op":"create","project_id":"<reservation-admin-project>","location":"<US|EU>","reservation_name":"<reservation_name>","assignment_project":"<assignment_project>","commitment_slots":100, "reservation_slots":100}`

How to delete all flex slots?
`{"flex_op":"delete","project_id":"<reservation-admin-project>","location":"<US|EU>"}`

### Quickstart
1.  The implementation is done using [Google Cloud Functions](https://cloud.google.com/functions/docs/concepts/overview)
2.  Create a new project in [GCP Console](https://console.cloud.google.com/projectcreate)
3.  Enable required APIs from GCP APIs & Service such as Cloud Build API, Cloud Functions API, [Cloud Resource Manager API](https://cloud.google.com/resource-manager/reference/rest)
4.  Create a new topic by running `scripts/create-pubsub-topic.sh` or [manually](https://cloud.google.com/pubsub/docs/quickstart-console)
5.  Configure the IAM permission for cloud build service account `<project-number>@cloudbuild.gserviceaccount.com` with **Cloud Functions Admin** and **Service Account User** roles
6.  The steps of the pipeline are given in the `cloudbuild.yaml` file
7.  Cloud function deployed using the `scripts/deploy-stage.sh` script
8.  Setup the new cloud build trigger connecting with github/bitbucket repository
9.  Commit the code into the connected repository to deploy the cloud function 

The idea is to schedule the publish which can be done using [cloud scheduler](https://cloud.google.com/scheduler/docs)

`gcloud scheduler jobs create pubsub JOB --schedule=SCHEDULE --topic=TOPIC (--message-body=MESSAGE_BODY | --message-body-from-file=MESSAGE_BODY_FROM_FILE) [optional flags]`

The following creates / schedules the topic triggered cloud function to create flex slots during work days morning 9 AM:

`gcloud scheduler jobs create pubsub create-flex --schedule "0 9 * * 1-5" --topic stage_bq_flex_slot_trigger --message-body "{"flex_op":"create","project_id":"<reservation-admin-project>","location":"<US|EU>","reservation_name":"<reservation_name>","assignment_project":"<assignment_project>","commitment_slots":100, "reservation_slots":100}"`

The following creates / schedules the topic triggered cloud function to delete all flex slots during work days at 6 PM:

`gcloud scheduler jobs create pubsub delete-flex --schedule "0 18 * * 1-5" --topic stage_bq_flex_slot_trigger --message-body "{"flex_op":"delete","project_id":"<reservation-admin-project>","location":"<US|EU>"}"`



