let available_voices;
let available_voicesURI;
var socket = io();

socket.on('connect_', function(message) {
    window.tts_volume = message.tts_volume;
    window.tts_rate = message.tts_rate;
    window.tts_voice = message.tts_vc;
    socket.emit('connect_');
});

if(window.speechSynthesis.getVoices().length === 0) {
    window.speechSynthesis.addEventListener('voiceschanged', function() {
        available_voices = window.speechSynthesis.getVoices();
        available_voicesURI = available_voices.map(voice => `\n${voice.voiceURI}`);
        console.log(`found voices:${available_voicesURI}`);
    });
} else {
    available_voices = window.speechSynthesis.getVoices();
    available_voicesURI = available_voices.map(voice => `\n${voice.voiceURI}`);
    console.log(`found voices:${available_voicesURI}`);
}

function prepareTextToSpeechMsg(data) {
    let voice = available_voices.find(SpeechSynthesisVoice => SpeechSynthesisVoice.voiceURI === data['voice']);
    if (voice === undefined)
        return console.log(`voice is undefined, found voices:${available_voicesURI}`);
    let utter = new SpeechSynthesisUtterance();
    utter.rate = window.tts_rate;
    utter.volume = window.tts_volume;
    utter.text = data['message'];
    utter.voice = voice;
    return utter;
}

function sayMessage(data) {
    let message = prepareTextToSpeechMsg(data);
    if (message === undefined)
        return console.log('speech object is undefined, expected SpeechSynthesisUtterance');
    window.speechSynthesis.speak(message);
}

socket.on('tts', function(message) {
    sayMessage(message);
});

socket.on('tts_set_attr', function(message) {
    window[message.attr] = message.value;
    if (!message.response)
        return;
    socket.emit('tts_attr_response', {'attr': message.attr, 
                                      'value': window[message.attr]});
});

socket.on('tts_get_attr', function(message) {
    socket.emit('tts_attr_response', {'attr': message.attr, 
                                      'value': window[message.attr]});
});

socket.on('tts_get_cfg', function() {
    socket.emit('tts_get_cfg', {'tts_vol': window.tts_volume,
                                'tts_rate': window.tts_rate,
                                'tts_vc': window.tts_voice});
});
