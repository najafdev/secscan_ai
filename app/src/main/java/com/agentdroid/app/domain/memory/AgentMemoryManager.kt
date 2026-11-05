package com.agentdroid.app.domain.memory

import com.agentdroid.app.data.local.dao.MemoryDao
import com.agentdroid.app.data.local.entity.MemoryRecordEntity
import com.agentdroid.app.domain.model.AgentRole
import com.agentdroid.app.domain.model.MemoryRecord
import com.agentdroid.app.domain.model.MemoryTier
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import java.util.UUID

class AgentMemoryManager(private val memoryDao: MemoryDao) {

    fun getAllRecords(): Flow<List<MemoryRecord>> {
        return memoryDao.getAllMemoryRecords().map { entities ->
            entities.map { it.toDomain() }
        }
    }

    fun getRecordsByTier(tier: MemoryTier): Flow<List<MemoryRecord>> {
        return memoryDao.getMemoryByTier(tier.name).map { entities ->
            entities.map { it.toDomain() }
        }
    }

    suspend fun saveRecord(
        tier: MemoryTier,
        agentRole: AgentRole?,
        key: String,
        value: String,
        tags: List<String> = emptyList()
    ) {
        val entity = MemoryRecordEntity(
            id = UUID.randomUUID().toString(),
            tier = tier.name,
            agentRole = agentRole?.name,
            key = key,
            value = value,
            tagsJson = tags.joinToString(",", "[", "]") { "\"$it\"" }
        )
        memoryDao.insertMemory(entity)
    }

    suspend fun getRecordByKey(key: String): MemoryRecord? {
        val entity = memoryDao.getMemoryByKey(key) ?: return null
        memoryDao.incrementAccess(entity.id)
        return entity.toDomain()
    }

    suspend fun getMemoryContextForAgent(role: AgentRole): String {
        val records = memoryDao.getMemoryForAgent(role.name)
        if (records.isEmpty()) return ""
        return records.take(10).joinToString("\n") { "${it.key}: ${it.value}" }
    }

    suspend fun deleteRecord(id: String) {
        memoryDao.deleteMemory(id)
    }

    suspend fun clearTier(tier: MemoryTier) {
        memoryDao.clearTier(tier.name)
    }

    suspend fun clearAll() {
        memoryDao.clearAllMemory()
    }

    private fun MemoryRecordEntity.toDomain(): MemoryRecord {
        val tierEnum = try { MemoryTier.valueOf(tier) } catch (e: Exception) { MemoryTier.SESSION }
        val roleEnum = agentRole?.let { try { AgentRole.valueOf(it) } catch (e: Exception) { null } }
        return MemoryRecord(
            id = id,
            tier = tierEnum,
            agentRole = roleEnum,
            key = key,
            value = value,
            confidence = confidence,
            timestamp = timestamp,
            accessCount = accessCount
        )
    }
}
