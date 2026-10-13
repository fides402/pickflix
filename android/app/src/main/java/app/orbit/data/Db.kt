package app.orbit.data

import android.content.Context
import androidx.room.*
import kotlinx.coroutines.flow.Flow

@Entity(tableName = "saved")
data class SavedContact(
    @PrimaryKey val id: String,
    val name: String,
    val roles: String,
    val tracks: Int,
    val via: String,
    val contacted: Boolean = false,
    val addedAt: Long = System.currentTimeMillis(),
)

@Dao
interface SavedDao {
    @Query("SELECT * FROM saved ORDER BY addedAt DESC") fun all(): Flow<List<SavedContact>>
    @Insert(onConflict = OnConflictStrategy.REPLACE) suspend fun upsert(c: SavedContact)
    @Query("DELETE FROM saved WHERE id = :id") suspend fun delete(id: String)
    @Query("UPDATE saved SET contacted = :v WHERE id = :id") suspend fun setContacted(id: String, v: Boolean)
}

@Database(entities = [SavedContact::class], version = 1, exportSchema = false)
abstract class OrbitDb : RoomDatabase() {
    abstract fun saved(): SavedDao
    companion object {
        @Volatile private var inst: OrbitDb? = null
        fun get(ctx: Context): OrbitDb = inst ?: synchronized(this) {
            inst ?: Room.databaseBuilder(ctx.applicationContext, OrbitDb::class.java, "orbit.db").build().also { inst = it }
        }
    }
}

class Prefs(ctx: Context) {
    private val sp = ctx.getSharedPreferences("orbit", Context.MODE_PRIVATE)
    var geniusToken: String
        get() = sp.getString("genius", "") ?: ""
        set(v) = sp.edit().putString("genius", v.trim()).apply()
}
