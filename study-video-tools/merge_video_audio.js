const { spawn } = require('child_process');
const ffmpegPath = require('ffmpeg-static');

console.log('FFmpeg path:', ffmpegPath);

const videoInput = './REC-20260504133020.mp4';
const audioInput = './新录音 20.m4a';
const output = './merged_output.mp4';

if (!ffmpegPath || typeof ffmpegPath !== 'string') {
  console.error('FFmpeg not found!');
  process.exit(1);
}

const ffmpeg = spawn(ffmpegPath, [
  '-i', videoInput,
  '-i', audioInput,
  '-c:v', 'copy',
  '-c:a', 'aac',
  '-strict', 'experimental',
  '-map', '0:v:0',
  '-map', '1:a:0',
  '-shortest',
  output
]);

ffmpeg.stdout.on('data', (data) => {
  console.log(`stdout: ${data}`);
});

ffmpeg.stderr.on('data', (data) => {
  console.error(`stderr: ${data}`);
});

ffmpeg.on('close', (code) => {
  if (code === 0) {
    console.log(`Successfully merged video and audio into ${output}`);
  } else {
    console.error(`FFmpeg process exited with code ${code}`);
  }
});