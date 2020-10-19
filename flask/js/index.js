var socket = io();

socket.on('connect_', function(message) {
    let css = 'body { width: ' + message.width + 'px; height: ' + message.height + 'px; margin: 0; } ' + 
                'img { max-width: ' + message.width + 'px; max-height: ' + message.height + 'px; } ' + 
                'div.outer { position: relative; height: ' + message.height + 'px; } ' +
                'div.outer img { position: absolute; right: 0px; bottom: 0px; }',
        head = document.head || document.getElementsByTagName('head')[0],
        style = document.createElement('style');
    head.appendChild(style);
    style.appendChild(document.createTextNode(css));
    window.player_volume = message.player_volume;
    socket.emit('connect_');
});

socket.on('player_get_time', function() {
    if (!window.player_media)
    {
        socket.emit('player_get_attr', {'time': 0});
        socket.emit('player_end');
        return;
    }
    socket.emit('player_get_attr', {'time': Math.floor(window.player_media.currentTime)});
})

socket.on('player_set_media', async function(message) {
    window.player_media = new Audio(message.url);
    window.player_media.volume = window.player_volume;
});

socket.on('player_set_volume', function(message) {
    window.player_volume = message.sr_volume;
    if (!window.player_media)
    {
        socket.emit('player_end');
        return;
    }
    window.player_media.volume = window.player_volume;
});

socket.on('player_set_time', function(message) {
    if (!window.player_media)
    {
        socket.emit('player_end');
        return;
    }
    window.player_media.currentTime = message.seconds;
});

socket.on('player_play', function() {
    window.player_media.play()
                       .catch((error) => { console.log(error); socket.emit('player_end'); });
    socket.emit('player_play');
    window.player_media.onended = () => { socket.emit('player_end'); };
});

socket.on('player_pause', function() {
    if (!window.player_media)
    {
        socket.emit('player_end');
        return;
    }
    window.player_media.pause();
    socket.emit('player_pause');
});

socket.on('player_stop', function() {
    socket.emit('player_stop');
    if (!window.player_media)
        return;
    window.player_media.pause();
    window.player_media.currentTime = 0;
});

function set_image(width, height, src) {
    let img = document.getElementById('img');
    let new_img = new Image(width, height);
    new_img.id = 'img';
    new_img.src = src;
    document.getElementById('imgdiv').appendChild(new_img);
    img.parentNode.removeChild(img);
}
