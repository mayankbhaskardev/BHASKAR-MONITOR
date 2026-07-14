const axios = require("axios");


async function sendTelegram(message){


try{


await axios.post(

`https://api.telegram.org/bot${process.env.TELEGRAM_TOKEN}/sendMessage`,

{

chat_id:
process.env.TELEGRAM_CHAT_ID,


text:
message,


parse_mode:
"HTML"

}


);


console.log(
"Telegram notification sent"
);



}

catch(error){


console.log(

"Telegram Error:",
error.response?.data ||
error.message

);


}



}



module.exports={
sendTelegram
};