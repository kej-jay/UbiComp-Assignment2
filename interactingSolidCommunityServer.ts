import { createDpopHeader, generateDpopKeyPair } from '@inrupt/solid-client-authn-core';
import { buildAuthenticatedFetch } from '@inrupt/solid-client-authn-core';
import * as fs from 'fs';

import {
  universalAccess
} from "@inrupt/solid-client";

//import fetch from "node-fetch";
import fetch from 'cross-fetch';
import { userInfo } from 'os';
const getSecret = async(): Promise<any[]> => {

const response0 = await fetch('https://solid.interactions.ics.unisg.ch/idp/credentials/', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        // The email/password fields are those of your account.
        // The name field will be used when generating the ID of your token.
        body: JSON.stringify({ email: 'kayerik.jenss@student.unisg.ch', password: 'HalloJonas', name: 'kayPod' }),
    });
      
      // These are the identifier and secret of your token.
      // Store the secret somewhere safe as there is no way to request it again from the server!
      const { id, secret } = await response0.json();
      console.log("--This is id", id, "This is secret: ", secret);

    return [id,secret];
  }

const getToken = async (id: any, secret: any): Promise<any[]> =>  {
      // A key pair is needed for encryption.
      // This function from `solid-client-authn` generates such a pair for you.
      const dpopKey = await generateDpopKeyPair();

      // These are the ID and secret generated in the previous step.
      // Both the ID and the secret need to be form-encoded.
      const authString = `${encodeURIComponent(id)}:${encodeURIComponent(secret)}`;
      // This URL can be found by looking at the "token_endpoint" field at
      const tokenUrl = 'https://solid.interactions.ics.unisg.ch/.oidc/token';
      const response = await fetch(tokenUrl, {
        method: 'POST',
        headers: {
          // The header needs to be in base64 encoding.
          authorization: `Basic ${Buffer.from(authString).toString('base64')}`,
          'content-type': 'application/x-www-form-urlencoded',
          dpop: await createDpopHeader(tokenUrl, 'POST', dpopKey),
        },
        body: 'grant_type=client_credentials&scope=webid',
      });

      // This is the Access token that will be used to do an authenticated request to the server.
      // The JSON also contains an "expires_in" field in seconds, 
      // which you can use to know when you need request a new Access token.
      const { access_token: accessToken } = await response.json();

      console.log("--This is access token:", accessToken);
      // console.log("--This is dpop: ", dpopKey)

     return [dpopKey, accessToken];
}


 
 const runAsyncFunctions = async () => {
   //Get id an secret 
   const idInfo = await getSecret();
  //  console.log("*** The secret and id are: ", idInfo);
   
   //Get token and key
   const token = await getToken(idInfo[0], idInfo[1]);
  //  console.log("*** The token is: ", token);
   
   const authFetch = await buildAuthenticatedFetch(fetch, token[1], { dpopKey:token[0] });
 }

 export const getAuthedFetch = async () => {
  const idInfo = await getSecret();
  const token = await getToken(idInfo[0], idInfo[1]);
  
  return await buildAuthenticatedFetch(fetch, token[1], { dpopKey:token[0] });
}

export const getAcl = async () => {
  const authFetch = await getAuthedFetch();
  // TODO GET Acl of container (2.)
   let response = await authFetch('https://solid.interactions.ics.unisg.ch/kayPod/.acl');
   console.log(response.status);
   console.log(response.headers);
   return response;
}

export const workWithResources = async (fileName, body, isAcl, method) => {
  const authFetch = await getAuthedFetch();
  if (!isAcl) {
    // create "normal" resource
    return await authFetch('https://solid.interactions.ics.unisg.ch/kayPod/' + fileName, 
      {
        method,
        body,
      });
  }

  //set content type for acl callout
  return await authFetch('https://solid.interactions.ics.unisg.ch/kayPod/' + fileName, 
  {
    method,
    body,
    headers: {"Content-Type": "text/n3"},
  });
}

export const newResource = async (fileName, body, isAcl) => {
  return await workWithResources(fileName, body, isAcl, "PUT");
}

export const editResource = async (fileName, body, isAcl) => {
  return await workWithResources(fileName, body, isAcl, "PATCH");
}

const task3 = async () => {
  const aclTemplateSelf = "@prefix acl: <http://www.w3.org/ns/auth/acl#>. <#owner> a acl:Authorization;acl:default <./>;acl:accessTo <./>;acl:mode acl:Read, acl:Write, acl:Control;acl:agent <https://solid.interactions.ics.unisg.ch/kayPod/profile/card#me>."
  // a)
  await newResource("gazeData/", "", false);
  await newResource("test/", "", false);

  // b)
  await newResource("test/myhobbies.txt", "I have no time for them", false);
  
  // c)
  await newResource("gazeData/.acl", aclTemplateSelf, true);
  let result = await newResource("test/.acl", aclTemplateSelf, true);

  console.log(result);
}

export const shareWithMarcel = async (file) => {
  const authFetch = await getAuthedFetch();
  // After having issues, Marcel recommended library: @inrupt/solid-client, which we used
  return await universalAccess.setAgentAccess(
    file,
    "https://solid.interactions.ics.unisg.ch/Marcel/profile/card#me",
    { read: true, write: true }, 
    { fetch: authFetch }
  );
}

const task4 = async () => {
  // a)
  await newResource("test/myhobbies.txt.acl", "@prefix acl: <http://www.w3.org/ns/auth/acl#>. <#owner> a acl:Authorization;acl:default <./myhobbies.txt>;acl:accessTo <./myhobbies.txt>;acl:mode acl:Read, acl:Write, acl:Control;acl:agent <https://solid.interactions.ics.unisg.ch/kayPod/profile/card#me>.", true);
  await shareWithMarcel("https://solid.interactions.ics.unisg.ch/kayPod/test/myhobbies.txt");

  // b)
  await newResource("test/myFriendsInfo.txt", "I have no time for them", false);
  let result = await newResource("myFamilyInfo.txt", "I would like to have more time for them", false);

  console.log(result);
}

const task5 = async () => {
  // let result = await newResource("gazeData/currentActivity.ttl", 
  // "@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .@prefix foaf: <http://xmlns.com/foaf/0.1/> . @prefix prov: <http://www.w3.org/ns/prov#> . @prefix schema: <http://schema.org/> . @prefix bm: <http://bimerr.iot.linkeddata.es/def/occupancy-profile#> . <https://solid.interactions.ics.unisg.ch/kayPod/gazeData/currentActivity.ttl> a prov:Activity, schema:ReadAction; schema:name \"Read action\"^^xsd:string; prov:wasAssociatedWith <https://solid.interactions.ics.unisg.ch/kayPod/profile/card#me>; prov:used <https://solid.interactions.ics.unisg.ch/kayPod/gazeData/rawGazeData.csv>; prov:endedAtTime \"2022-10-14T02:02:02Z\"^^xsd:dateTime; bm:probability  \"0.87\"^^xsd:float. <https://solid.interactions.ics.unisg.ch/kayPod/profile/card#me> a foaf:Person, prov:Agent; foaf:name \"Kay Jenss\"; foaf:mbox <mailto:kayerik.jenss@student.unisg.ch>.", 
  // true);
  
  let result = await newResource(
    "gazeData/currentActivity.ttl.acl",
    `@prefix acl: <http://www.w3.org/ns/auth/acl#>. <#owner> a acl:Authorization;acl:default <./currentActivity.ttl>;acl:accessTo <./currentActivity.ttl>;acl:mode acl:Read, acl:Write, acl:Control;acl:agent <https://solid.interactions.ics.unisg.ch/kayPod/profile/card#me>.`,
    true);

  console.log(result);
}

//runAsyncFunctions()

// task3()
// task4()
// task5()

// run using 'ts-node-esm interactingSolidCommunityServer.ts'