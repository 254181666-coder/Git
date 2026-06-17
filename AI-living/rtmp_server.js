const NodeMediaServer = require('node-media-server');

const config = {
  rtmp: {
    port: 1935,
    chunk_size: 60000,
    gop_cache: true,
    ping: 30,
    ping_timeout: 60,
    max_connections: 100,
    pull_timeout: 10
  },
  http: {
    port: 8081,
    allow_origin: '*'
  }
};

var nms = new NodeMediaServer(config);

nms.on('prePlay', (id, StreamPath, args) => {
  console.log('[prePlay] Client connected:', id, StreamPath);
});

nms.on('postPlay', (id, StreamPath, args) => {
  console.log('[postPlay] Client playing:', id, StreamPath);
});

nms.on('prePublish', (id, StreamPath, args) => {
  console.log('[prePublish] Publisher connected:', id, StreamPath);
});

nms.on('postPublish', (id, StreamPath, args) => {
  console.log('[postPublish] Publisher started:', id, StreamPath);
});

nms.on('donePublish', (id, StreamPath, args) => {
  console.log('[donePublish] Publisher disconnected:', id, StreamPath);
});

nms.run();

console.log('RTMP Server running on port 1935');
console.log('HTTP Server running on port 8081');
console.log('RTMP URL: rtmp://localhost/live/test');