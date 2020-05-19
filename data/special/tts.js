let available_voices;
let available_voicesURI;

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

    if (voice === undefined) {
        return console.log(`voice is undefined, found voices:${available_voicesURI}`);
    }

	let utter = new SpeechSynthesisUtterance();
	utter.rate = window.tts_rate;
    utter.volume = window.tts_volume;
	utter.text = data['message'];
	utter.voice = voice;

    return utter;
}

function sayMessage(data) {
    let message = prepareTextToSpeechMsg(data);
    
    if (message === undefined) {
        return console.log('speech object is undefined, expected SpeechSynthesisUtterance');
    }

    window.speechSynthesis.speak(message);
}
