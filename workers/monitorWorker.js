const cron=require("node-cron");


const MonitorAccount =
require("../models/MonitorAccount");


const instagram =
require("../services/instagram");


const tracker =
require("../services/usernameTracker");




cron.schedule(
"*/5 * * * *",

async()=>{


console.log(
"Monitor cycle started"
);



const accounts =
await MonitorAccount.find();



for(const account of accounts){



try{


const profile =
await instagram.getProfile(
account.username
);



await tracker(profile);



}

catch(err){


console.log(
"Monitor Error:",
err.message
);


}



}



});
