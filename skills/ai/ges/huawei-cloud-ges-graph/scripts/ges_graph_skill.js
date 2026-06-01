#!/usr/bin/env node
/**
 * GES Graph Skill - Node.js Version
 * 华为云图引擎持久化版 (GES) SDK for Node.js
 * 支持Cypher查询、GQL查询、节点/边操作、导入导出等
 */

const https = require('https');
const http = require('http');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { URL } = require('url');

// ==================== 环境配置 ====================

class EnvConfig {
    static ENV_DIR = path.join(__dirname, '..', '.env');

    static ENV_VAR_MAPPING = {
        'GES_GRAPH_IP': 'graph_ip',
        'GES_GRAPH_PORT': 'graph_port',
        'GES_PROJECT_ID': 'project_id',
        'GES_GRAPH_NAME': 'graph_name',
        'GES_IAM_URL': 'iam_url',
        'GES_USERNAME': 'username',
        'GES_PASSWORD': 'password',
        'GES_DOMAIN_NAME': 'domain_name',
        'GES_REGION': 'region',
        'HUAWEI_CLOUD_AK': 'access_key',
        'HUAWEI_CLOUD_SK': 'secret_key',
    };

    static loadGesEnv() {
        const config = {};
        const envFile = path.join(EnvConfig.ENV_DIR, 'ges_env.csv');
        const fileConfig = EnvConfig._loadCsv(envFile);

        for (const [envVar, configKey] of Object.entries(EnvConfig.ENV_VAR_MAPPING)) {
            const envValue = process.env[envVar];
            if (envValue) {
                config[configKey] = envValue;
            } else if (fileConfig[configKey]) {
                config[configKey] = fileConfig[configKey];
            }
        }

        for (const [key, value] of Object.entries(fileConfig)) {
            if (!config[key]) {
                config[key] = value;
            }
        }

        const requiredFields = ['graph_ip', 'project_id', 'graph_name', 'iam_url', 'username', 'password', 'domain_name', 'region'];
        const missingFields = requiredFields.filter(field => !config[field]);

        if (missingFields.length > 0) {
            console.error('==============================================');
            console.error('⚠️  配置缺失或不完整');
            console.error('==============================================');
            console.error('\n请通过以下方式配置（环境变量优先）：');
            console.error('  - 环境变量: GES_GRAPH_IP, GES_PROJECT_ID, GES_GRAPH_NAME, GES_IAM_URL, GES_REGION');
            console.error('  - AKSK: HUAWEI_CLOUD_AK, HUAWEI_CLOUD_SK');
            console.error('  - 或用户名密码: GES_USERNAME, GES_PASSWORD, GES_DOMAIN_NAME');
            console.error('  - 或配置文件: .env/ges_env.csv');
            console.error('\n缺失的必需配置项:');
            missingFields.forEach(field => console.error(`  - ${field}`));
            console.error('==============================================\n');
        }

        return config;
    }

    static _loadCsv(filepath) {
        const config = {};
        if (fs.existsSync(filepath)) {
            const content = fs.readFileSync(filepath, 'utf-8');
            const lines = content.trim().split('\n');
            for (let i = 1; i < lines.length; i++) {
                const parts = lines[i].split(',');
                if (parts.length >= 2) {
                    config[parts[0].trim()] = parts[1].trim();
                }
            }
        }
        return config;
    }
}

// ==================== Token管理 ====================

class TokenManager {
    constructor() {
        this.token = null;
        this.tokenExpiry = 0;
        this.config = EnvConfig.loadGesEnv();
    }

    async getToken() {
        const currentTime = Date.now();
        if (this.token && currentTime < this.tokenExpiry - 300000) { // 提前5分钟过期
            return this.token;
        }

        const envToken = process.env.GES_TOKEN;
        if (envToken) {
            this.token = envToken;
            this.tokenExpiry = Date.now() + 3600 * 23 * 1000;
            return this.token;
        }

        const accessKey = this.config.access_key;
        const secretKey = this.config.secret_key;

        if (accessKey && secretKey) {
            try {
                this.token = await this._fetchTokenByAksk();
                return this.token;
            } catch (e) {
                console.log(`AKSK方式获取Token失败，尝试密码方式: ${e.message}`);
            }
        }

        const username = this.config.username;
        const password = this.config.password;
        const domainName = this.config.domain_name;

        if (username && password) {
            try {
                this.token = await this._fetchTokenByPassword(username, password, domainName);
                return this.token;
            } catch (e) {
                throw new Error(`密码方式获取Token也失败了: ${e.message}`);
            }
        }

        throw new Error("无法获取Token，请配置AKSK或用户名密码");
    }

    async _fetchTokenByPassword(username, password, domainName) {
        const url = this.config.iam_url;
        const projectId = this.config.project_id;

        if (!url) {
            throw new Error("ges_env.csv中缺少iam_url配置");
        }

        let data;
        if (domainName) {
            data = JSON.stringify({
                auth: {
                    identity: {
                        methods: ['password'],
                        password: {
                            user: {
                                name: username,
                                password: password,
                                domain: { name: domainName }
                            }
                        }
                    },
                    scope: { project: { id: projectId } }
                }
            });
        } else {
            data = JSON.stringify({
                auth: {
                    identity: {
                        methods: ['password'],
                        password: {
                            user: {
                                name: username,
                                password: password
                            }
                        }
                    },
                    scope: { project: { id: projectId } }
                }
            });
        }

        const resp = await this._makeRequest(url, 'POST', data, {
            'Content-Type': 'application/json'
        });

        const token = resp.headers['x-subject-token'];
        if (!token) {
            throw new Error(`密码获取Token失败，未获取到token`);
        }

        this.tokenExpiry = Date.now() + 3600 * 23 * 1000;
        return token;
    }

    async _fetchTokenByAksk() {
        const accessKey = this.config.access_key;
        const secretKey = this.config.secret_key;
        const projectId = this.config.project_id;
        const url = this.config.iam_url;
        const region = this.config.region || 'cn-north-7';

        if (!url) {
            throw new Error("ges_env.csv中缺少iam_url配置");
        }

        const Service = 'iam';
        const ContentType = 'application/json;charset=UTF-8';

        const Body = JSON.stringify({
            auth: {
                identity: {
                    methods: ['hw_access_key'],
                    hw_access_key: {
                        access: { key: accessKey }
                    }
                },
                scope: { project: { id: projectId } }
            }
        });

        // 签名计算
        const BasicDateFormat = "%Y%m%dT%H%M%SZ";
        const ScopeDateFormat = "%Y%m%d";
        const Algorithm = "HWS-HMAC-SHA256";

        const sign = (key, msg) => {
            return crypto.createHmac('sha256', key).update(msg).digest();
        };

        const getSignatureKey = (key, dateStamp, region, service) => {
            const kDate = sign(Buffer.from('HWS' + key), dateStamp);
            const kRegion = sign(kDate, region);
            const kService = sign(kRegion, service);
            return sign(kService, 'hws_request');
        };

        const now = new Date();
        const hwsDate = now.toISOString().replace(/[-:]/g, '').replace(/\.\d{3}/, '');
        const dateStamp = now.toISOString().slice(0, 10).replace(/-/g, '');

        const canonicalUri = '/v3/auth/tokens/';
        const canonicalHeaders = `accept:${'application/json'}\ncontent-type:${ContentType}\nx-hws-date:${hwsDate}\n`;
        const signedHeaders = 'accept;content-type;x-hws-date';
        const payloadHash = crypto.createHash('sha256').update(Body).digest('hex');

        const canonicalRequest = [
            'POST', canonicalUri, '', canonicalHeaders, signedHeaders, payloadHash
        ].join('\n');

        const credentialScope = [dateStamp, region, Service, 'hws_request'].join('/');
        const stringToSign = [
            Algorithm, hwsDate, credentialScope,
            crypto.createHash('sha256').update(canonicalRequest).digest('hex')
        ].join('\n');

        const signingKey = getSignatureKey(secretKey, dateStamp, region, Service);
        const signature = crypto.createHmac('sha256', signingKey).update(stringToSign).digest('hex');

        const authorizationHeader = `${Algorithm} Credential=${accessKey}/${credentialScope}, SignedHeaders=${signedHeaders}, Signature=${signature}`;

        const headers = {
            'Accept': 'application/json',
            'Content-Type': ContentType,
            'X-Hws-Date': hwsDate,
            'X-Identity-Sign': authorizationHeader
        };

        const resp = await this._makeRequest(url, 'POST', Body, headers);

        const token = resp.headers['x-subject-token'];
        if (!token) {
            throw new Error(`AKSK获取Token失败，未获取到token`);
        }

        this.tokenExpiry = Date.now() + 3600 * 23 * 1000;
        return token;
    }

    _makeRequest(urlStr, method, data, headers) {
        return new Promise((resolve, reject) => {
            const url = new URL(urlStr);
            const isHttps = url.protocol === 'https:';
            const lib = isHttps ? https : http;

            const options = {
                hostname: url.hostname,
                port: url.port || (isHttps ? 443 : 80),
                path: url.pathname,
                method: method,
                headers: headers,
                timeout: 30000
            };

            const req = lib.request(options, (res) => {
                let body = '';
                res.on('data', chunk => body += chunk);
                res.on('end', () => {
                    resolve({
                        statusCode: res.statusCode,
                        headers: res.headers,
                        body: body
                    });
                });
            });

            req.on('error', reject);
            req.on('timeout', () => reject(new Error('Request timeout')));

            if (data) {
                req.write(data);
            }
            req.end();
        });
    }
}

// ==================== OBS客户端 ====================

/**
 * OBS客户端 - 使用虚拟主机方式访问
 *
 * 虚拟主机URL格式: https://bucketname.obs.region.domain/objectkey
 *
 * 签名算法: Authorization: OBS AccessKeyID:Signature
 * 其中: Signature = Base64(HMAC-SHA1(Your_SK, UTF8(StringToSign)))
 *
 * StringToSign格式:
 * - 无Content-Type: METHOD\n\n\nDate\n/bucket/key
 * - 有Content-Type: METHOD\n\nContent-Type\nDate\n/bucket/key
 */
class OBSClient {
    constructor(accessKey, secretKey, region = "cn-north-7") {
        this.accessKey = accessKey;
        this.secretKey = secretKey;
        this.region = region;
        // 使用虚拟主机方式: bucket.obs.endpoint
        this.endpoint = `obs.${region}.ulanqab.huawei.com`;
        this.available = Boolean(accessKey && secretKey);
    }

    isAvailable() {
        return this.available;
    }

    /**
     * 生成OBS签名
     * @param {string} stringToSign - 待签名字符串
     */
    _sign(stringToSign) {
        const crypto = require('crypto');
        const hmac = crypto.createHmac('sha1', this.secretKey);
        hmac.update(stringToSign, 'utf8');
        return hmac.digest('base64');
    }

    /**
     * 发起OBS请求
     * @param {string} method - HTTP方法
     * @param {string} bucket - 桶名
     * @param {string} objectKey - 对象键
     * @param {object} options - 选项
     */
    async _request(method, bucket, objectKey = '', options = {}) {
        const { query = {}, headers = {}, body = null } = options;

        // 构造查询字符串 (实际请求路径)
        const queryString = Object.entries(query)
            .map(([k, v]) => `${k}=${encodeURIComponent(v)}`)
            .join('&');
        const actualPath = objectKey ? `/${objectKey}` : '/';
        const fullPath = queryString ? `${actualPath}?${queryString}` : actualPath;

        // 生成签名 - OBS签名格式
        const date = new Date().toUTCString();
        const contentType = headers['Content-Type'] || '';

        let stringToSign;
        const signPath = objectKey ? `/${bucket}/${objectKey}` : `/${bucket}/`;

        if (contentType) {
            // 有Content-Type时的签名格式: METHOD\n\nContent-Type\nDate\n/path
            stringToSign = [
                method,
                '\n',
                '\n',
                contentType,
                '\n',
                date,
                '\n',
                signPath
            ].join('');
        } else {
            // 无Content-Type时的签名格式: METHOD\n\n\nDate\n/path (3个换行)
            stringToSign = [
                method,
                '\n',
                '\n',
                '\n',
                date,
                '\n',
                signPath
            ].join('');
        }

        const signature = this._sign(stringToSign);

        // 构建请求头
        const requestHeaders = {
            'Host': `${bucket}.${this.endpoint}`,
            'Date': date,
            'Authorization': `OBS ${this.accessKey}:${signature}`,
            ...headers
        };

        return new Promise((resolve, reject) => {
            const req = https.request({
                hostname: `${bucket}.${this.endpoint}`,
                port: 443,
                path: fullPath,
                method: method,
                headers: requestHeaders
            }, (res) => {
                const chunks = [];
                res.on('data', chunk => chunks.push(chunk));
                res.on('end', () => {
                    const body = Buffer.concat(chunks).toString();
                    if (res.statusCode >= 400) {
                        reject(new Error(`OBS请求失败 [${res.statusCode}]: ${body}`));
                        return;
                    }
                    try {
                        resolve({ statusCode: res.statusCode, body: JSON.parse(body) });
                    } catch {
                        resolve({ statusCode: res.statusCode, body: body });
                    }
                });
            });

            req.on('error', reject);
            if (body) req.write(body);
            req.end();
        });
    }

    /**
     * 列出桶中对象
     * @param {string} bucket - 桶名
     * @param {string} prefix - 前缀过滤
     */
    async listObjects(bucket, prefix = "") {
        if (!this.available) {
            throw new Error("OBS客户端不可用，请配置access_key和secret_key");
        }

        const result = await this._request('GET', bucket, '', {
            query: { 'list-type': '2', prefix: prefix }
        });

        // 解析XML响应
        const contents = [];
        const regex = /<Contents><Key>([^<]+)<\/Key><LastModified>([^<]+)<\/LastModified><ETag>([^<]+)<\/ETag><Size>(\d+)<\/Size>/g;
        let match;
        while ((match = regex.exec(result.body)) !== null) {
            contents.push({
                Key: match[1],
                LastModified: match[2],
                ETag: match[3],
                Size: parseInt(match[4])
            });
        }
        return contents;
    }

    /**
     * 上传文件到OBS
     * @param {string} localFile - 本地文件路径
     * @param {string} bucket - 桶名
     * @param {string} objectKey - OBS中的对象键
     */
    async uploadFile(localFile, bucket, objectKey) {
        if (!this.available) {
            throw new Error("OBS客户端不可用");
        }

        const fs = require('fs');
        if (!fs.existsSync(localFile)) {
            throw new Error(`文件不存在: ${localFile}`);
        }

        const fileContent = fs.readFileSync(localFile);

        await this._request('PUT', bucket, objectKey, {
            headers: {
                'Content-Type': 'application/octet-stream',
                'Content-Length': fileContent.length
            },
            body: fileContent
        });

        return true;
    }

    /**
     * 从OBS下载文件
     * @param {string} bucket - 桶名
     * @param {string} objectKey - OBS中的对象键
     * @param {string} localFile - 本地保存路径
     */
    async downloadFile(bucket, objectKey, localFile) {
        if (!this.available) {
            throw new Error("OBS客户端不可用");
        }

        const fs = require('fs');

        const result = await this._request('GET', bucket, objectKey);
        fs.writeFileSync(localFile, result.body);
        return true;
    }

    /**
     * 删除OBS中的对象
     * @param {string} bucket - 桶名
     * @param {string} objectKey - OBS中的对象键
     */
    async deleteObject(bucket, objectKey) {
        if (!this.available) {
            throw new Error("OBS客户端不可用");
        }

        await this._request('DELETE', bucket, objectKey);
        return true;
    }

    /**
     * 获取对象URL
     * @param {string} bucket - 桶名
     * @param {string} objectKey - OBS中的对象键
     */
    getObjectUrl(bucket, objectKey) {
        return `https://${bucket}.${this.endpoint}/${objectKey}`;
    }
}
// ==================== GES客户端 ====================

class GESClient {
    constructor() {
        this.tokenMgr = new TokenManager();
        this.config = EnvConfig.loadGesEnv();
        this.graphIp = this.config.graph_ip || '';
        this.graphPort = this.config.graph_port || '80';
        this.projectId = this.config.project_id || '';
        this.graphName = this.config.graph_name || '';
        this.baseUrl = `http://${this.graphIp}:${this.graphPort}/ges/v1.0/${this.projectId}/graphs/${this.graphName}`;

        // 初始化OBS客户端
        const accessKey = this.config.access_key || '';
        const secretKey = this.config.secret_key || '';
        const region = this.config.region || 'cn-north-7';
        if (accessKey && secretKey) {
            this.obsClient = new OBSClient(accessKey, secretKey, region);
        } else {
            this.obsClient = null;
        }
    }

    getObsClient() {
        return this.obsClient;
    }

    async _getHeaders() {
        return {
            'X-Auth-Token': await this.tokenMgr.getToken(),
            'Content-Type': 'application/json'
        };
    }

    async _request(method, path, data = null, params = null) {
        let url = `${this.baseUrl}${path}`;
        
        if (params) {
            const queryString = Object.entries(params)
                .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`)
                .join('&');
            url += (url.includes('?') ? '&' : '?') + queryString;
        }

        const headers = await this._getHeaders();
        
        // 使用原生http模块发送请求
        const urlObj = new URL(url);
        const isHttps = urlObj.protocol === 'https:';
        const lib = isHttps ? https : http;

        return new Promise((resolve, reject) => {
            const options = {
                hostname: urlObj.hostname,
                port: urlObj.port || (isHttps ? 443 : 80),
                path: urlObj.pathname + urlObj.search,
                method: method,
                headers: headers,
                timeout: 60000,
                rejectUnauthorized: false
            };

            const req = lib.request(options, (res) => {
                let body = '';
                res.on('data', chunk => body += chunk);
                res.on('end', () => {
                    if (res.statusCode >= 400) {
                        reject(new Error(`API请求失败 [${res.statusCode}]: ${body}`));
                        return;
                    }
                    try {
                        resolve(JSON.parse(body));
                    } catch {
                        resolve({ raw: body });
                    }
                });
            });

            req.on('error', reject);
            req.on('timeout', () => reject(new Error('Request timeout')));

            if (data) {
                req.write(JSON.stringify(data));
            }
            req.end();
        });
    }

    // ==================== Cypher查询相关API ====================

    async executeCypher(statement, parameters = null, executionMode = "sync", 
                       resultDataContents = "row", limit = 1000) {
        const data = {
            statements: [{
                statement: statement,
                parameters: parameters || {},
                executionMode: executionMode,
                resultDataContents: [resultDataContents],
                limit: limit
            }]
        };

        return this._request('POST', `/action?action_id=execute-cypher-query`, data);
    }

    async executeCypherAsync(statement, parameters = null, resultDataContents = "row") {
        const result = await this.executeCypher(statement, parameters, "async", resultDataContents);
        // jobId可能在顶层或results[0]中
        return result.jobId || (result.results && result.results[0] && result.results[0].jobId) || '';
    }

    async getJobStatus(jobId) {
        return this._request('GET', `/jobs/${jobId}/status`);
    }

    // ==================== GQL查询相关API ====================

    async executeGql(statement, parameters = null, executionMode = "sync",
                    resultDataContents = "row", limit = 1000, includeStats = true) {
        const data = {
            statements: [{
                statement: statement,
                parameters: parameters || {},
                executionMode: executionMode,
                resultDataContents: [resultDataContents],
                limit: limit,
                includeStats: includeStats
            }]
        };

        return this._request('POST', `/action?action_id=execute-gql-query`, data);
    }

    async executeGqlAsync(statement, parameters = null, resultDataContents = "row") {
        const result = await this.executeGql(statement, parameters, "async", resultDataContents);
        // jobId可能在顶层或results[0]中
        return result.jobId || (result.results && result.results[0] && result.results[0].jobId) || '';
    }

    // ==================== Schema相关API ====================

    async getSchema() {
        return this.executeCypher("call db.schema()", null, "sync", "graph");
    }

    async createOrUpdateLabel(label, properties, labelType = "vertex") {
        const data = {
            name: label,
            type: labelType,
            properties: []
        };

        for (const prop of properties) {
            data.properties.push({
                property: {
                    name: prop.name,
                    dataType: prop.dataType || "string",
                    cardinality: prop.cardinality || "single"
                }
            });
        }

        return this._request('POST', '/schema/labels', data);
    }

    async getLabelSchema(label) {
        return this._request('GET', `/schema?label=${label}`);
    }

    async createEdgeType(edgeType, properties = null) {
        const data = {
            type: "edge",
            properties: []
        };

        if (properties) {
            for (const prop of properties) {
                data.properties.push({
                    property: {
                        name: prop.name,
                        dataType: prop.dataType || "string",
                        cardinality: prop.cardinality || "single"
                    }
                });
            }
        }

        return this._request('POST', `/schema?label=${edgeType}`, data);
    }

    async getGraphSummary(labelDetails = false) {
        return this._request('GET', `/summary?label_details=${labelDetails}`);
    }

    // ==================== 节点操作API ====================

    async addNode(nodeId, labels = null, properties = null) {
        labels = labels || [];
        properties = properties || {};

        const labelStr = labels.length > 0 ? ':' + labels.join(':') : '';
        
        const propsStr = Object.keys(properties).map(k => `${k}: $${k}`).join(', ');
        const propsClause = propsStr ? `, ${propsStr}` : '';

        const statement = `CREATE (n${labelStr} {_ID_: $id${propsClause}}) RETURN n`;
        const params = { id: nodeId, ...properties };

        return this.executeCypher(statement, params);
    }

    async addNodesBatch(nodes) {
        const statements = [];

        for (let i = 0; i < nodes.length; i++) {
            const node = nodes[i];
            const nodeId = node.id;
            const labels = node.labels || [];
            const properties = node.properties || {};

            if (!nodeId) continue;

            const labelStr = labels.length > 0 ? ':' + labels.join(':') : '';
            const propsStr = Object.keys(properties).map(k => `${k}: $${k}_${i}`).join(', ');
            const propsClause = propsStr ? `, ${propsStr}` : '';

            const statement = `CREATE (n${labelStr} {_ID_: $id_${i}${propsClause}})`;
            
            const params = { [`id_${i}`]: nodeId };
            for (const [k, v] of Object.entries(properties)) {
                params[`${k}_${i}`] = v;
            }

            statements.push({
                statement: statement,
                parameters: params,
                resultDataContents: ["row"]
            });
        }

        const data = { statements: statements };
        return this._request('POST', '/action?action_id=execute-cypher-query', data);
    }

    async deleteNode(nodeId) {
        const statement = "MATCH (n) WHERE id(n) = $id DETACH DELETE n";
        return this.executeCypher(statement, { id: nodeId });
    }

    async updateNode(nodeId, properties) {
        const propsStr = Object.keys(properties).map(k => `n.${k} = $${k}`).join(', ');
        const statement = `MATCH (n) WHERE id(n) = $id SET ${propsStr} RETURN n`;
        const params = { id: nodeId, ...properties };
        return this.executeCypher(statement, params);
    }

    async getNode(nodeId) {
        const statement = "MATCH (n) WHERE id(n) = $id RETURN n";
        return this.executeCypher(statement, { id: nodeId });
    }

    // ==================== 边操作API ====================

    async addEdge(startNodeId, endNodeId, edgeType, properties = null) {
        properties = properties || {};

        let propsClause = '';
        if (Object.keys(properties).length > 0) {
            const propsStr = Object.keys(properties).map(k => `${k}: $${k}`).join(', ');
            propsClause = ` {${propsStr}}`;
        }

        const statement = `MATCH (a), (b) WHERE id(a) = $start AND id(b) = $end CREATE (a)-[r:${edgeType}${propsClause}]->(b) RETURN r`;
        const params = { start: startNodeId, end: endNodeId, ...properties };

        return this.executeCypher(statement, params);
    }

    async deleteEdge(startNodeId, endNodeId, edgeType = null) {
        let statement;
        if (edgeType) {
            statement = `MATCH (a)-[r:${edgeType}]->(b) WHERE id(a) = $start AND id(b) = $end DELETE r`;
        } else {
            statement = "MATCH (a)-[r]->(b) WHERE id(a) = $start AND id(b) = $end DELETE r";
        }

        return this.executeCypher(statement, { start: startNodeId, end: endNodeId });
    }

    async getEdges(nodeId, direction = "both") {
        let statement;
        if (direction === "out") {
            statement = "MATCH (n)-[r]->(m) WHERE id(n) = $id RETURN r, m";
        } else if (direction === "in") {
            statement = "MATCH (n)<-[r]-(m) WHERE id(n) = $id RETURN r, m";
        } else {
            statement = "MATCH (n)-[r]-(m) WHERE id(n) = $id RETURN r, m";
        }

        return this.executeCypher(statement, { id: nodeId });
    }

    // ==================== Label操作API ====================

    async addLabelToNode(nodeId, label) {
        const statement = "MATCH (n) WHERE id(n) = $id SET n:`$label` RETURN n";
        return this.executeCypher(statement, { id: nodeId, label: label });
    }

    async removeLabelFromNode(nodeId, label) {
        // GES不支持直接移除label
        const statement = "MATCH (n) WHERE id(n) = $id RETURN n";
        return this.executeCypher(statement, { id: nodeId });
    }

    async getNodesByLabel(label, limit = 100) {
        const statement = `MATCH (n:\`${label}\`) RETURN n LIMIT ${limit}`;
        return this.executeCypher(statement);
    }

    // ==================== 导入导出API ====================

    async exportGraph(exportPath, vertexSetName = "set_vertex", 
                     edgeSetName = "set_edge", schemaName = "schema.xml", 
                     obsParameters = null) {
        const data = {
            graphExportPath: exportPath,
            vertexSetName: vertexSetName,
            edgeSetName: edgeSetName,
            schemaName: schemaName
        };

        if (obsParameters) {
            data.obsParameters = obsParameters;
        }

        const resp = await this._request('POST', '/action?action_id=export-graph', data);
        return resp.jobId || '';
    }

    async importGraph(schemaPath, vertexPath = null, edgePath = null, obsParameters = null) {
        const data = { schemaPath: schemaPath };

        if (vertexPath) data.vertexsetPath = vertexPath;
        if (edgePath) data.edgesetPath = edgePath;
        if (obsParameters) data.obsParameters = obsParameters;

        const resp = await this._request('POST', '/action?action_id=import-graph', data);
        return resp.jobId || '';
    }

    // ==================== 图管理API ====================

    async clearGraph(useApi = true) {
        if (useApi) {
            return this._request('POST', '/action?action_id=clear-graph', {});
        } else {
            const statement = "MATCH (n) DETACH DELETE n";
            return this.executeCypher(statement);
        }
    }

    async getGraphStats() {
        return this.getGraphSummary(true);
    }

    // ==================== 索引操作API ====================

    async createVertexIndex(indexName, label = null) {
        const data = {
            indexName: indexName,
            indexType: "GlobalCompositeVertexIndex",
            hasLabel: Boolean(label),
            indexProperty: []
        };

        return this._request('POST', '/indices', data);
    }

    async createEdgeIndex(indexName, label = null) {
        const data = {
            indexName: indexName,
            indexType: "GlobalCompositeEdgeIndex",
            hasLabel: Boolean(label),
            indexProperty: []
        };

        return this._request('POST', '/indices', data);
    }
}

// ==================== GES Graph Skill主类 ====================

class GESGraphSkill {
    constructor() {
        this.client = new GESClient();
    }

    // ==================== 高级操作接口 ====================

    async _ensureLabelProperties(label, newProperties) {
        // 获取已有属性列表
        const schema = await this.client.getLabelSchema(label);
        const existingProps = [];

        // 解析已有属性
        if (schema && schema.results && schema.results[0]) {
            const data = schema.results[0].data;
            if (data && data.length > 0) {
                const properties = data[0].row[0].properties || [];
                for (const prop of properties) {
                    existingProps.push({
                        property: {
                            name: prop.name,
                            dataType: prop.dataType,
                            cardinality: prop.cardinality || "single"
                        }
                    });
                }
            }
        }

        // 合并新属性（去重）
        const existingNames = new Set(existingProps.map(p => p.property.name));
        for (const prop of newProperties) {
            if (!existingNames.has(prop.property.name)) {
                existingProps.push(prop);
            }
        }

        // 如果没有新属性要添加，直接返回
        if (existingProps.length === 0 && newProperties.length === 0) {
            return;
        }

        // 更新Label Schema（追加新属性）
        const data = {
            type: "vertex",
            properties: existingProps
        };

        await this.client._request('POST', `/schema?label=${label}`, data);
    }

    async executeQuery(cypher, parameters = null) {
        return this.client.executeCypher(cypher, parameters);
    }

    async executeGql(gql, parameters = null) {
        return this.client.executeGql(gql, parameters);
    }

    async getSchemaInfo() {
        return this.client.getSchema();
    }

    async getStatistics() {
        return this.client.getGraphStats();
    }

}

// ==================== 便捷函数 ====================

function getClient() {
    return new GESClient();
}

function getSkill() {
    return new GESGraphSkill();
}

// ==================== 导出 ====================

module.exports = {
    GESClient,
    GESGraphSkill,
    TokenManager,
    OBSClient,
    getClient,
    getSkill
};

// ==================== 主程序测试 ====================

if (require.main === module) {
    (async () => {
        const skill = new GESGraphSkill();

        console.log("=== 测试获取Token ===");
        try {
            const token = await skill.client.tokenMgr.getToken();
            console.log(`Token获取成功: ${token.substring(0, 20)}...`);
        } catch (e) {
            console.log(`Token获取失败: ${e.message}`);
        }

        console.log("\n=== 测试GQL API ===");
        console.log("\n1. 执行GQL查询: MATCH (n) RETURN n LIMIT 3");
        try {
            const result = await skill.executeGql("MATCH (n) RETURN n LIMIT 3");
            console.log(`结果: ${JSON.stringify(result).substring(0, 500)}...`);
        } catch (e) {
            console.log(`错误: ${e.message}`);
        }

        console.log("\n2. 执行GQL统计: MATCH (n) RETURN count(*) as total");
        try {
            const result = await skill.executeGql("MATCH (n) RETURN count(*) as total");
            console.log(`结果: ${JSON.stringify(result).substring(0, 500)}...`);
        } catch (e) {
            console.log(`错误: ${e.message}`);
        }

        console.log("\n=== 测试Cypher API ===");
        console.log("\n1. 执行Cypher查询: MATCH (n) RETURN n LIMIT 3");
        try {
            const result = await skill.executeQuery("MATCH (n) RETURN n LIMIT 3");
            console.log(`结果: ${JSON.stringify(result).substring(0, 500)}...`);
        } catch (e) {
            console.log(`错误: ${e.message}`);
        }
    })();
}
