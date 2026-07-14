const MonitorAccount =
require("../models/MonitorAccount");


const notify =
require("./notification");



async function trackUsername(profile){


const account =
await MonitorAccount.findOne({
    instagramId:profile.id
});



if(!account){

console.log(
"New account added"
);


return;

}




if(account.username !== profile.username){



console.log(
`
USERNAME CHANGE DETECTED

OLD:
${account.username}

NEW:
${profile.username}
`
);



const event={


oldUsername:
account.username,


newUsername:
profile.username,


changedAt:
new Date()


};




account.usernameHistory.push(event);



account.username =
profile.username;



await account.save();



await notify.usernameChanged(event);



return {
changed:true,
event
};



}




account.lastChecked =
new Date();



await account.save();



return {

changed:false

};



}



module.exports =
trackUsername;