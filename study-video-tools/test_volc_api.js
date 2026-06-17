const https = require('https');

const API_KEY = 'ark-2b040029-9400-46e5-9240-8f4a3137bded-9af0a';
const BASE_URL = 'ark.cn-beijing.volces.com';

const data = JSON.stringify({
  model: 'claude-3-sonnet-20240229',
  messages: [
    { role: 'user', content: '你好' }
  ],
  max_tokens: 100
});

console.log('正在测试火山引擎API...');
console.log(`API Key: ${API_KEY.substring(0, 10)}...`);
console.log('---');

const paths = [
  '/api/v3/messages',
  '/v1/messages',
  '/claude/v1/messages',
  '/api/v3/chat/completions',
  '/v1/chat/completions'
];

function testPath(index) {
  if (index >= paths.length) {
    console.log('\n所有路径测试完毕，请查看火山引擎API文档获取正确路径');
    return;
  }

  const path = paths[index];
  console.log(`\n=== 测试路径 ${index + 1}: ${path} ===`);

  const options = {
    hostname: BASE_URL,
    port: 443,
    path: path,
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${API_KEY}`,
      'anthropic-version': '2023-06-01'
    }
  };

  console.log(`URL: https://${options.hostname}${options.path}`);

  const req = https.request(options, (res) => {
    console.log(`状态码: ${res.statusCode}`);

    let body = '';
    res.on('data', (chunk) => {
      body += chunk;
    });

    res.on('end', () => {
      if (res.statusCode === 200) {
        console.log('✅ 成功!');
        try {
          const result = JSON.parse(body);
          console.log('响应:', JSON.stringify(result, null, 2));
        } catch (e) {
          console.log('响应:', body);
        }
      } else if (res.statusCode === 404) {
        console.log('❌ 路径不存在，继续测试下一个...');
        testPath(index + 1);
      } else {
        console.log('❌ 其他错误');
        try {
          console.log('错误:', JSON.stringify(JSON.parse(body), null, 2));
        } catch (e) {
          console.log('错误:', body);
        }
      }
    });
  });

  req.on('error', (error) => {
    console.error('请求错误:', error);
    testPath(index + 1);
  });

  req.write(data);
  req.end();
}

testPath(0);
