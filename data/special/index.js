var socket = io();

socket.on('connect_', function(data) {
    let css = 'body { width: ' + data['screenwidth'] + 'px; height: ' + data['screenheight'] + 'px; margin: 0; } ' + 
                'img { max-width: ' + data['screenwidth'] + 'px; max-height: ' + data['screenheight'] + 'px; } ' + 
                'div.outer { position: relative; height: ' + data['screenheight'] + 'px; } ' +
                'div.outer img { position: absolute; right: 0px; bottom: 0px; }',
        head = document.head || document.getElementsByTagName('head')[0],
        style = document.createElement('style');
    head.appendChild(style);
    style.appendChild(document.createTextNode(css));
    window.tts_volume = data['tts_volume'];
    window.tts_rate = data['tts_rate'];
    window.tts_voice = data['tts_voice']
});

socket.on('tts', function(data) {
    sayMessage(data);
});

socket.on('tts_setProperty', function(data) {
    window[data['attr']] = data['value'];
    if (data['response'] === 'False') {
        return
    }
    socket.emit('tts_PropertyResponse', {'attr': data['attr'], 'value': window[data['attr']]});
});

socket.on('tts_getProperty', function(data) {
    socket.emit('tts_PropertyResponse', {'attr': data['attr'], 'value': window[data['attr']]});
});

function set_image(width, height, src) {
    let img = document.getElementById('img');
    let new_img = new Image(width, height);
    new_img.id = 'img';
    new_img.src = src;
    document.getElementById('imgdiv').appendChild(new_img);
    img.parentNode.removeChild(img);
}