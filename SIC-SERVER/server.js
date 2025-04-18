const fs = require("fs")
const express = require("express")
const mqtt = require("mqtt")
require("dotenv").config()

const app = express()

const client_id = `server_${ Math.random().toString().slice(3) }`
const mqtt_url = `mqtt://broker.emqx.io:1883`
const mqtt_topic = ["/SIC/SHENDOCK/TTS"]

const client_mqtt = mqtt.connect(
    mqtt_url,
    {
        clientId: client_id,
        clean: true,
        connectTimeout: 4000,
        username: "",
        password: "",
        reconnectPeriod: 1000
    }
)

client_mqtt.on("connect", () => {
    console.log(`Connnected to ${ mqtt_url }`)

    mqtt_topic.forEach(item => {
        client_mqtt.subscribe([item], () => {
            console.log(`Subscribe to topic ${ item }`)
        })
    })
})

client_mqtt.on("message", (topic, payload) => {
    console.log(`Receiver message from ${ topic }, message: ${ payload }`)
})

app.use(express.json())
app.use(express.urlencoded({ extended: true }))

app.post(
    "/api/camera",
    (req, res) => {
        try {
            if(req.body?.image) {
                fs.writeFileSync("image.txt", req.body.image, (err) => {
                    if (err) {
                        console.log(err)
                    }
                })

                if(!client_mqtt.connected) {
                    console.log("MQTT not connected.")

                    return res.status(200).json({
                        message: "MQTT not connected.",
                        status: true
                    })
                }

                client_mqtt.publish(
                    mqtt_topic[0],
                    JSON.stringify({
                        "text": "Tembok terdeteksi."
                    }),
                    {
                        qos: 0,
                        retain: false
                    },
                    (error) => {
                        if(error) {
                            console.log(error)
                        }
                    }
                )

                return res.status(200).json({
                    message: "Success.",
                    status: true
                })
            }
        } catch (error) {
            console.log(error)

            return res.status(400).json({
                message: "Failed.",
                status: false
            })
        }
    }
)

app.listen(8000, "192.168.46.218" ,() => {
    console.log("Server is running on 192.168.46.218:8000.")
})