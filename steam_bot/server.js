const SteamUser = require('steam-user');
const csgo = require("csgo")
const express = require('express');
const protobuf = require("protobufjs");
const EventEmitter = require('events');
const Long = require("long");
require('dotenv').config()


const PORT = process.env.PORT || 3000
const STEAM_LOGIN = process.env.STEAM_LOGIN || '' 
const STEAM_PASSWORD = process.env.STEAM_PASSWORD || '' 

const app = express();

const csgoEvents = new EventEmitter(); 
const client = new SteamUser();


const LOGIN_DETAILS = {
  accountName: STEAM_LOGIN,
  password: STEAM_PASSWORD, 
};


client.logOn(LOGIN_DETAILS);

client.on('loggedOn', () => {
  console.log('Успешный вход в Steam');
  client.setPersona(SteamUser.EPersonaState.Invisible);
  client.gamesPlayed([730]); 
});

client.on('error', (err) => {
  console.error('Ошибка Steam:', err);
});


client.on('appLaunched', (appid) => {
  if (appid === 730) {
    console.log('CS2 готов к работе');
  }
});

client.on('receivedFromGC', (appid, msgType, payload) => {
    console.log(`Received message ${msgType} from GC ${appid} with ${payload.length} bytes`)
    if (appid == 730 && msgType == 9139)
      protobuf.load('Protobufs/csgo/cstrike15_gcmessages.proto', (err, root) => {
        let matchId
        if (err)
          throw err;
        try {
          const CMsgGCCStrike15_v2_MatchList = root.lookupType('CMsgGCCStrike15_v2_MatchList')
          const buffer = CMsgGCCStrike15_v2_MatchList.decode(payload)
          const message = CMsgGCCStrike15_v2_MatchList.toObject(buffer)

          const matchIdStruct = message.matches[0].matchid
          console.log(matchIdStruct)
          matchId = Long.fromBits(matchIdStruct.low, matchIdStruct.high, matchIdStruct.unsigned)
          const matchUrl = message.matches[0].roundstatsall.at(-1).map
          const matchTime = message.matches[0].matchtime

          csgoEvents.emit('matchUrl/' + matchId.toString(), {"matchUrl": matchUrl, "matchTime": matchTime});
          console.log("Ответ от сервера для matchID " + matchId.toString())
        }
        catch (err){
          console.error("Оштбка ", err)
          csgoEvents.emit('error/' + matchId.toString(), err);
        }
          
      })
});


app.get('/getDemoLink', async (req, res) => {
  const sharecode = req.query.sharecode;

  if (!sharecode) {
    return res.status(400).json({ error: 'Не указан sharecode' });
  }

  const decoded = new csgo.SharecodeDecoder(sharecode).decode()

  if (!decoded) {
    return res.status(400).json({ error: 'Ошибка в sharecode' });
  }

  try {
    const matchData = await new Promise((resolve, reject) => {
        const timeout = setTimeout(() => {
          reject(new Error('Превышено время ожидания ответа от GC'));
        }, 10000); 
  
        csgoEvents.once('matchUrl/' + decoded['matchId'].toString(), (data) => {
          clearTimeout(timeout);
          resolve(data);
        });
  
        csgoEvents.once('error/' + decoded['matchId'].toString(), (err) => {
          clearTimeout(timeout);
          reject(err);
        });
  
        protobuf.load('Protobufs/csgo/cstrike15_gcmessages.proto', (err, root) => {
            if (err)
              throw err;
            const CMsgGCCStrike15_v2_MatchListRequestFullGameInfo = root.lookupType('CMsgGCCStrike15_v2_MatchListRequestFullGameInfo')
            payload = {
              matchid: decoded['matchId'],
              outcomeid: decoded['outcomeId'],
              token: decoded['tokenId']
            };

            console.log("Отправка сообщения для matchId " + decoded['matchId'].toString())
      
            const message = CMsgGCCStrike15_v2_MatchListRequestFullGameInfo.create(payload);
      
            const buffer = CMsgGCCStrike15_v2_MatchListRequestFullGameInfo.encode(message).finish();
      
            client.sendToGC(730, 9147, {}, buffer);
          })
      });

    if(matchData['error']){
      const error = matchData['error']
      console.error('Ошибка:', error);
      res.status(500).json({ error: 'Не удалось получить демо' });
    }

    console.log("Ответ:")
    console.log(matchData)
    console.log("для matchId: " + decoded['matchId'].toString())
    res.json({ matchData });

  } catch (err) {
    console.error('Ошибка:', err);
    res.status(500).json({ error: 'Не удалось получить демо' });
  }
});

app.listen(PORT, () => {
  console.log(`Сервер запущен на http://localhost:${PORT}`);
});