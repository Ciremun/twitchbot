var socket = io();

socket.on('connect_', function(data) {
    var css = 'body { width: ' + data['screenwidth'] + 'px; height: ' + data['screenheight'] + 'px; margin: 0; } ' + 
                'img { max-width: ' + data['screenwidth'] + 'px; max-height: ' + data['screenheight'] + 'px; } ' + 
                'div.outer { position: relative; height: ' + data['screenheight'] + 'px; } ' +
                'div.outer img { position: absolute; right: 0px; bottom: 0px; }',
        head = document.head || document.getElementsByTagName('head')[0],
        style = document.createElement('style');
    head.appendChild(style);
    style.appendChild(document.createTextNode(css));
});

function set_image(width, height, src) {
    var img = document.getElementById('img');
    var new_img = new Image(width, height);
    new_img.id = 'img';
    new_img.src = src;
    document.getElementById('imgdiv').appendChild(new_img);
    img.parentNode.removeChild(img);
}