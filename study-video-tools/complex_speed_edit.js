const { spawn } = require('child_process');
const ffmpegPath = require('ffmpeg-static');

console.log('FFmpeg path:', ffmpegPath);

const inputFile = './a61a2225d3b33f34146f8c8fce3b8346.mov';
const outputFile = './complex_speed_output.mp4';
const segment1End = '30';
const segment2End = '210';
const speed = '2';

async function run() {
  return new Promise((resolve, reject) => {
    const ffmpeg = spawn(ffmpegPath, [
      '-y',
      '-i', inputFile,
      '-filter_complex', `
        [0:v]trim=start=0:end=${segment1End},setpts=PTS-STARTPTS[v0];
        [0:a]atrim=start=0:end=${segment1End},asetpts=PTS-STARTPTS[a0];
        [0:v]trim=start=${segment1End}:end=${segment2End},setpts=PTS-STARTPTS,setpts=${1/parseFloat(speed)}*PTS[v1];
        [0:a]atrim=start=${segment1End}:end=${segment2End},asetpts=PTS-STARTPTS,atempo=${speed}[a1];
        [0:v]trim=start=${segment2End},setpts=PTS-STARTPTS[v2];
        [0:a]atrim=start=${segment2End},asetpts=PTS-STARTPTS[a2];
        [v0][a0][v1][a1][v2][a2]concat=n=3:v=1:a=1[v][a]
      `.replace(/\s+/g, ' '),
      '-map', '[v]',
      '-map', '[a]',
      '-c:v', 'libx264',
      '-crf', '23',
      '-c:a', 'aac',
      '-strict', 'experimental',
      outputFile
    ]);

    ffmpeg.stderr.on('data', (data) => {
      console.error(`stderr: ${data}`);
    });

    ffmpeg.on('close', (code) => {
      if (code === 0) {
        console.log(`Successfully created: ${outputFile}`);
        resolve();
      } else {
        reject(new Error(`Process exited with code ${code}`));
      }
    });
  });
}

run().catch(console.error);