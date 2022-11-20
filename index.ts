import express from 'express';
import { getAuthedFetch, newResource, shareWithMarcel } from "./interactingSolidCommunityServer";
import * as fs from 'fs';
import {
    buildThing,
    getDatetime,
    getDecimal,
    getSolidDataset,
    getStringNoLocale,
    getThing,
    saveSolidDatasetAt,
    setThing,
} from "@inrupt/solid-client";

const app = express();

app.post('/updateActivity', async (req, res) => {
    let action = req.query.action;
    const probability = req.query.probability;
    let schema = "";

    if (action === "Reading") {
        action = "Read";
        schema = "https://schema.org/ReadAction";
    } else if (action === "Search") {
        action = "Searching";
        schema = "https://schema.org/SearchAction";
    } else {
        action = "Inspection";
        schema = "https://schema.org/CheckAction";
    }

    // read local file from path
    const csvContent = fs.readFileSync('./Data/RawGazeData3/00_unknown.csv','utf8');
    //console.log(csvContent);

    // patch csv content
    const csvName =  "gazeData/" + Date.now() + ".csv";
    const csvReq = await newResource(csvName, csvContent, false);

    let authFetch = await getAuthedFetch();
    let myDataset = await getSolidDataset(
        "https://solid.interactions.ics.unisg.ch/kayPod/gazeData/currentActivity.ttl",
        { fetch: authFetch }
    );

    let activityThing = getThing(myDataset, "https://solid.interactions.ics.unisg.ch/kayPod/gazeData/currentActivity.ttl");
    activityThing = buildThing(activityThing)
        .setStringNoLocale("http://www.w3.org/ns/prov#Activity", action)
        .setStringNoLocale("http://schema.org/name", action + " action")
        .setStringNoLocale("http://www.w3.org/ns/prov#used", "https://solid.interactions.ics.unisg.ch/kayPod/" + csvName)
        .setDatetime("http://www.w3.org/ns/prov#endedAtTime", new Date())
        .setDecimal("http://bimerr.iot.linkeddata.es/def/occupancy-profile#probability", Number(probability))
        .build();

    myDataset = setThing(myDataset, activityThing);

    authFetch = await getAuthedFetch();
    await saveSolidDatasetAt(
        "https://solid.interactions.ics.unisg.ch/kayPod/gazeData/currentActivity.ttl",
        myDataset,
        { fetch: authFetch } 
    );
    
    res.send({"action": action, probability, "csv_status": csvReq.status, "ttl_status": JSON.parse(JSON.stringify(activityThing))});
})


app.get('/activity', async (req, res) => {
    const activityFile = "https://solid.interactions.ics.unisg.ch/kayPod/gazeData/currentActivity.ttl";
    let authFetch = await getAuthedFetch();
    let myDataset = await getSolidDataset(activityFile, { fetch: authFetch });

    const activityThing = getThing(myDataset, "https://solid.interactions.ics.unisg.ch/kayPod/gazeData/currentActivity.ttl");
    const probability = getDecimal(activityThing, "http://bimerr.iot.linkeddata.es/def/occupancy-profile#probability");
    const time = getDatetime(activityThing, "http://www.w3.org/ns/prov#endedAtTime");
    const activity = getStringNoLocale(activityThing, "http://schema.org/name")
    
    const nameNode = activityThing["predicates"]["http://www.w3.org/ns/prov#wasAssociatedWith"]["namedNodes"][0]
    const nameThing = getThing(myDataset, nameNode);
    const name = getStringNoLocale(nameThing, "http://xmlns.com/foaf/0.1/name")
    
    // res.send({activity, name, probability, time});
    res.send(activity + "\n" + name + "\n" + probability + "\n" + time);
})


app.post('/shareWithMarcel', async (req, res) => {
   await shareWithMarcel("https://solid.interactions.ics.unisg.ch/kayPod/gazeData/currentActivity.ttl");
   console.log("Shared with Marcel");
    res.send("success");
})

app.listen(3000, () => {
    console.log('The application is listening on port 3000!');
})

// run using 'npx ts-node index.ts'