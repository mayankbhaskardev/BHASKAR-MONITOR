const telegram =
require("./telegram");


const discord =
require("./discord");



async function usernameChanged(data){



const message =

`
🚨 <b>BHASKAR MONITOR ALERT</b>


📌 Event:
Username Changed


👤 Previous:
@${data.oldUsername}


➡️ New:
@${data.newUsername}


🕒 Time:
${data.changedAt}

`;



await telegram.sendTelegram(
message
);



await discord.sendDiscord(
message
);



}



module.exports={

usernameChanged

};