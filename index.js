require("dotenv").config();


require("./config/database");


require("./workers/monitorWorker");


console.log(
`
🔥 Bhaskar Monitor Started
`
);