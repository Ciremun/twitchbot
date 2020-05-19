
if(window.speechSynthesis.getVoices().length == 0) {
	window.speechSynthesis.addEventListener('voiceschanged', function() {
	});
}

function prepareTextToSpeechMsg(data) {
	let available_voices = window.speechSynthesis.getVoices();
    let voice = available_voices.find(SpeechSynthesisVoice => SpeechSynthesisVoice.voiceURI === data['voice']);

    if (voice === undefined) {
        return console.log(`voice is undefined, found voices:${available_voices.map(voice => `\n${voice.voiceURI}`)}`);
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
