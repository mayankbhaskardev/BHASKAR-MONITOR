const mongoose = require("mongoose");


const historySchema = new mongoose.Schema({

    oldUsername:{
        type:String,
        required:true
    },

    newUsername:{
        type:String,
        required:true
    },

    changedAt:{
        type:Date,
        default:Date.now
    }

},{_id:false});



const monitorSchema = new mongoose.Schema({

    instagramId:{
        type:String,
        required:true,
        unique:true,
        index:true
    },


    username:{
        type:String,
        required:true
    },


    usernameHistory:[
        historySchema
    ],


    status:{
        type:String,
        enum:[
            "ACTIVE",
            "DISABLED",
            "UNKNOWN"
        ],

        default:"UNKNOWN"
    },


    lastChecked:{
        type:Date,
        default:Date.now
    }

},{

timestamps:true

});


module.exports =
mongoose.model(
"MonitorAccount",
monitorSchema
);